import logging
import unittest
from typing import Any, Callable, Optional, cast

from rmf_dispenser_msgs.msg import DispenserState
from rmf_door_msgs.msg import DoorMode
from rmf_fleet_msgs.msg import RobotMode
from rmf_ingestor_msgs.msg import IngestorState
from rmf_lift_msgs.msg import LiftState
from rx.core.observable.observable import Observable
from rx.scheduler.historicalscheduler import HistoricalScheduler
from rx.subject.subject import Subject
from tortoise import Tortoise

from api_server.models import (
    DispenserHealth,
    DoorHealth,
    HealthStatus,
    IngestorHealth,
    LiftHealth,
    RobotHealth,
)
from api_server.models.health import BaseBasicHealth
from api_server.test import init_db, test_data

from .events import RmfEvents
from .health_watchdog import HealthWatchdog


class BaseFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()

        self.scheduler = HistoricalScheduler()
        self.rmf = RmfEvents()
        self.logger = logging.Logger("test")
        self.logger.setLevel("CRITICAL")
        self.health_watchdog = HealthWatchdog(
            self.rmf, scheduler=self.scheduler, logger=self.logger
        )

    async def asyncTearDown(self):
        await Tortoise().close_connections()


async def check_heartbeat(
    test: BaseFixture,
    health_obs: Observable,
    source: Subject,
    factory: Callable[[str], Any],
):
    """
    :param health_obs: Observable[BasicHealthModel], the observable of the heartbeat events
    :param source: Observable[SourceType], the observable that should trigger heartbeat events
    :param factory: Callable[[str], SourceType], a factory function that returns an object of
        the source observable sequence type
    """
    health: BaseBasicHealth = cast(Any, None)

    def assign(v):
        nonlocal health
        health = v

    health_obs.subscribe(assign)

    source.on_next(factory("test_id"))
    test.assertEqual(health.health_status, HealthStatus.HEALTHY)
    test.assertEqual(health.id_, "test_id")

    # it should not be dead yet
    test.scheduler.advance_by(HealthWatchdog.LIVELINESS / 2)
    test.assertEqual(health.health_status, HealthStatus.HEALTHY)
    test.assertEqual(health.id_, "test_id")

    # # it should be dead now because the time between states has reached the threshold
    test.scheduler.advance_by(HealthWatchdog.LIVELINESS / 2)
    test.assertEqual(health.health_status, HealthStatus.DEAD)
    test.assertEqual(health.id_, "test_id")

    # # it should become alive again when a new state is emitted
    source.on_next(factory("test_id"))
    test.assertEqual(health.health_status, HealthStatus.HEALTHY)
    test.assertEqual(health.id_, "test_id")


class TestHealthWatchdog_DoorHealth(BaseFixture):
    async def test_heartbeat(self):
        await self.health_watchdog.start()
        await check_heartbeat(
            self, self.rmf.door_health, self.rmf.door_states, test_data.make_door_state
        )

    async def test_door_mode(self):
        test_cases = [
            (DoorMode.MODE_CLOSED, HealthStatus.HEALTHY),
            (DoorMode.MODE_MOVING, HealthStatus.HEALTHY),
            (DoorMode.MODE_OPEN, HealthStatus.HEALTHY),
            (DoorMode.MODE_OFFLINE, HealthStatus.UNHEALTHY),
            (DoorMode.MODE_UNKNOWN, HealthStatus.UNHEALTHY),
            (128, HealthStatus.UNHEALTHY),
        ]
        for test in test_cases:
            door_state = test_data.make_door_state("test_door")
            door_state.current_mode.value = test[0]
            health = HealthWatchdog.door_mode_to_health(door_state)
            self.assertIsNotNone(health)
            health = cast(DoorHealth, health)
            self.assertEqual(health.health_status, test[1])

    async def test_heartbeat_with_no_state(self):
        building_map = test_data.make_building_map()
        building_map.levels[0].doors = [test_data.make_door("test_door")]
        await building_map.save()
        await self.health_watchdog.start()

        health: Optional[DoorHealth] = None

        def assign(v):
            nonlocal health
            health = v

        self.rmf.door_health.subscribe(assign)

        self.scheduler.advance_by(self.health_watchdog.LIVELINESS)
        self.assertIsNotNone(health)
        health = cast(DoorHealth, health)
        self.assertEqual(health.id_, "test_door")
        self.assertEqual(health.health_status, HealthStatus.DEAD)


class TestHealthWatchdog_LiftHealth(BaseFixture):
    async def test_heartbeat(self):
        await self.health_watchdog.start()
        self.scheduler.advance_by(1)
        await check_heartbeat(
            self, self.rmf.lift_health, self.rmf.lift_states, test_data.make_lift_state
        )

    async def test_heartbeat_with_no_state(self):
        """
        Tests that a lift that never sends any state can be caught by the heartbeat watchdog.
        This also tests that the list of known lifts is automatically updated when a new
        building map comes in.
        """
        building_map = test_data.make_building_map()
        building_map.lifts = [test_data.make_lift("test_lift")]
        await building_map.save()
        await self.health_watchdog.start()

        health: Optional[LiftHealth] = None

        def assign(v):
            nonlocal health
            health = v

        self.rmf.lift_health.subscribe(assign)

        self.scheduler.advance_by(self.health_watchdog.LIVELINESS)
        self.assertIsNotNone(health)
        health = cast(LiftHealth, health)
        self.assertEqual(health.id_, "test_lift")
        self.assertEqual(health.health_status, HealthStatus.DEAD)

    async def test_lift_mode(self):
        test_cases = [
            (LiftState.MODE_HUMAN, HealthStatus.HEALTHY),
            (LiftState.MODE_AGV, HealthStatus.HEALTHY),
            (LiftState.MODE_UNKNOWN, HealthStatus.UNHEALTHY),
            (LiftState.MODE_FIRE, HealthStatus.UNHEALTHY),
            (LiftState.MODE_EMERGENCY, HealthStatus.UNHEALTHY),
            (LiftState.MODE_OFFLINE, HealthStatus.UNHEALTHY),
            (128, HealthStatus.UNHEALTHY),
        ]
        for test in test_cases:
            lift_state = test_data.make_lift_state("test_lift")
            lift_state.current_mode = test[0]
            health = HealthWatchdog.lift_mode_to_health(lift_state)
            self.assertIsNotNone(health)
            health = cast(LiftHealth, health)
            self.assertEqual(health.health_status, test[1])


class TestHealthWatchdog_DispenserHealth(BaseFixture):
    async def test_heartbeat(self):
        await self.health_watchdog.start()
        await check_heartbeat(
            self,
            self.rmf.dispenser_health,
            self.rmf.dispenser_states,
            test_data.make_dispenser_state,
        )

    async def test_heartbeat_with_no_state(self):
        await test_data.make_dispenser_state("test_dispenser").save()
        await self.health_watchdog.start()

        health: Optional[DispenserHealth] = None

        def assign(v):
            nonlocal health
            health = v

        self.rmf.dispenser_health.subscribe(assign)

        self.scheduler.advance_by(self.health_watchdog.LIVELINESS)
        self.assertIsNotNone(health)
        health = cast(DispenserHealth, health)
        self.assertEqual(health.id_, "test_dispenser")
        self.assertEqual(health.health_status, HealthStatus.DEAD)

    async def test_dispenser_mode_to_health(self):
        test_cases = [
            (DispenserState.IDLE, HealthStatus.HEALTHY),
            (DispenserState.BUSY, HealthStatus.HEALTHY),
            (DispenserState.OFFLINE, HealthStatus.UNHEALTHY),
            (128, HealthStatus.UNHEALTHY),
        ]
        for test in test_cases:
            dispenser_state = test_data.make_dispenser_state("test_dispenser")
            dispenser_state.mode = test[0]
            health = HealthWatchdog.dispenser_mode_to_health(dispenser_state)
            self.assertIsNotNone(health)
            health = cast(DispenserHealth, health)
            self.assertEqual(health.health_status, test[1])


class TestHealthWatchdog_IngestorHealth(BaseFixture):
    async def test_heartbeat(self):
        await self.health_watchdog.start()
        await check_heartbeat(
            self,
            self.rmf.ingestor_health,
            self.rmf.ingestor_states,
            test_data.make_ingestor_state,
        )

    async def test_heartbeat_with_no_state(self):
        await test_data.make_ingestor_state("test_ingestor").save()
        await self.health_watchdog.start()

        health: Optional[IngestorHealth] = None

        def assign(v):
            nonlocal health
            health = v

        self.rmf.ingestor_health.subscribe(assign)

        self.scheduler.advance_by(self.health_watchdog.LIVELINESS)
        self.assertIsNotNone(health)
        health = cast(IngestorHealth, health)
        self.assertEqual(health.id_, "test_ingestor")
        self.assertEqual(health.health_status, HealthStatus.DEAD)

    async def test_ingestor_mode_to_health(self):
        test_cases = [
            (IngestorState.IDLE, HealthStatus.HEALTHY),
            (IngestorState.BUSY, HealthStatus.HEALTHY),
            (IngestorState.OFFLINE, HealthStatus.UNHEALTHY),
            (128, HealthStatus.UNHEALTHY),
        ]
        for test in test_cases:
            ingestor_state = test_data.make_ingestor_state("test_ingestor")
            ingestor_state.mode = test[0]
            health = HealthWatchdog.ingestor_mode_to_health(ingestor_state)
            self.assertEqual(health.health_status, test[1])


class TestHealthWatchdog_RobotHealth(BaseFixture):
    async def test_heartbeat(self):
        await self.health_watchdog.start()

        health = None

        def assign(v):
            nonlocal health
            health = v

        self.rmf.robot_health.subscribe(assign)

        def factory():
            state = test_data.make_fleet_state("test_fleet")
            state.robots = [test_data.make_robot_state("test_robot")]
            return state

        robot_id = "test_fleet/test_robot"
        self.rmf.fleet_states.on_next(factory())
        self.assertIsNotNone(health)
        health = cast(RobotHealth, health)
        self.assertEqual(health.health_status, HealthStatus.HEALTHY)
        self.assertEqual(health.id_, robot_id)

        # it should not be dead yet
        self.scheduler.advance_by(HealthWatchdog.LIVELINESS / 2)
        self.assertIsNotNone(health)
        health = cast(RobotHealth, health)
        self.assertEqual(health.health_status, HealthStatus.HEALTHY)
        self.assertEqual(health.id_, robot_id)

        # # it should be dead now because the time between states has reached the threshold
        self.scheduler.advance_by(HealthWatchdog.LIVELINESS / 2)
        self.assertIsNotNone(health)
        health = cast(RobotHealth, health)
        self.assertEqual(health.health_status, HealthStatus.DEAD)
        self.assertEqual(health.id_, robot_id)

        # # it should become alive again when a new state is emitted
        self.rmf.fleet_states.on_next(factory())
        self.assertIsNotNone(health)
        health = cast(RobotHealth, health)
        self.assertEqual(health.health_status, HealthStatus.HEALTHY)
        self.assertEqual(health.id_, robot_id)

    async def test_heartbeat_with_no_state(self):
        await test_data.make_fleet_state("test_fleet").save()
        await self.health_watchdog.start()

        def factory():
            state = test_data.make_fleet_state("test_fleet")
            state.robots = [test_data.make_robot_state("test_robot")]
            return state

        self.rmf.fleet_states.on_next(factory())

        health: Optional[RobotHealth] = None

        def assign(v):
            nonlocal health
            health = v

        self.rmf.robot_health.subscribe(assign)

        robot_id = "test_fleet/test_robot"
        self.scheduler.advance_by(self.health_watchdog.LIVELINESS)
        self.assertIsNotNone(health)
        health = cast(RobotHealth, health)
        self.assertEqual(health.id_, robot_id)
        self.assertEqual(health.health_status, HealthStatus.DEAD)

    async def test_robot_mode(self):
        test_cases = [
            (RobotMode.MODE_IDLE, HealthStatus.HEALTHY),
            (RobotMode.MODE_CHARGING, HealthStatus.HEALTHY),
            (RobotMode.MODE_MOVING, HealthStatus.HEALTHY),
            (RobotMode.MODE_PAUSED, HealthStatus.HEALTHY),
            (RobotMode.MODE_WAITING, HealthStatus.HEALTHY),
            (RobotMode.MODE_GOING_HOME, HealthStatus.HEALTHY),
            (RobotMode.MODE_DOCKING, HealthStatus.HEALTHY),
            (RobotMode.MODE_EMERGENCY, HealthStatus.UNHEALTHY),
            (RobotMode.MODE_ADAPTER_ERROR, HealthStatus.UNHEALTHY),
            (128, HealthStatus.UNHEALTHY),
        ]
        for test in test_cases:
            robot_state = test_data.make_robot_state("test_robot")
            robot_state.mode.mode = test[0]
            health = HealthWatchdog.robot_mode_to_health(
                "test_fleet/test_robot", robot_state
            )
            self.assertIsNotNone(health)
            health = cast(RobotHealth, health)
            self.assertEqual(health.health_status, test[1])
