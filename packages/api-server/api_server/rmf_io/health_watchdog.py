import logging
from typing import Any, Dict, List, Optional, cast

from rmf_dispenser_msgs.msg import DispenserState as RmfDispenserState
from rmf_door_msgs.msg import DoorMode as RmfDoorMode
from rmf_fleet_msgs.msg import RobotMode as RmfRobotMode
from rmf_ingestor_msgs.msg import IngestorState as RmfIngestorState
from rmf_lift_msgs.msg import LiftState as RmfLiftState
from rx import operators as ops
from rx.core.observable.observable import Observable
from rx.core.pipe import pipe
from rx.core.typing import Disposable
from rx.scheduler.scheduler import Scheduler
from rx.subject.behaviorsubject import BehaviorSubject

from api_server.models import (
    BuildingMap,
    Dispenser,
    DispenserHealth,
    DispenserState,
    DoorHealth,
    DoorState,
    FleetState,
    HealthStatus,
    Ingestor,
    IngestorHealth,
    IngestorState,
    LiftHealth,
    LiftState,
    RobotHealth,
    RobotState,
)
from api_server.models import tortoise_models as ttm

from .events import RmfEvents
from .operators import heartbeat, most_critical


class HealthWatchdog:
    LIVELINESS = 10

    def __init__(
        self,
        rmf_events: RmfEvents,
        *,
        scheduler: Optional[Scheduler] = None,
        logger: logging.Logger = None,
    ):
        self.rmf = rmf_events
        self.scheduler = scheduler
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._building_watchers: List[Disposable] = []

    async def start(self):
        await self._watch_door_health()
        await self._watch_lift_health()
        await self._watch_dispenser_health()
        await self._watch_ingestor_health()
        await self._watch_robot_health()

    @staticmethod
    def _combine_most_critical(*obs: Observable):
        """
        Combines an observable sequence of an observable sequence of BasicHealthModel to an
        observable sequence of BasicHealthModel with the most critical health status. If there
        are multiple BasicHealthModel with the same criticality, the most recent item is
        chosen.

        :param obs: Sequence[rx.Observable[BasicHealthModel]]
        """
        return pipe(
            ops.timestamp(),
            ops.combine_latest(*[x.pipe(ops.timestamp()) for x in obs]),
            most_critical(),
        )

    @staticmethod
    def door_mode_to_health(state: Optional[DoorState]) -> Optional[DoorHealth]:
        if state is None:
            return None

        if state.current_mode.value in (
            RmfDoorMode.MODE_CLOSED,
            RmfDoorMode.MODE_MOVING,
            RmfDoorMode.MODE_OPEN,
        ):
            return DoorHealth(
                id_=state.door_name,
                health_status=HealthStatus.HEALTHY,
            )
        if state.current_mode.value == RmfDoorMode.MODE_OFFLINE:
            return DoorHealth(
                id_=state.door_name,
                health_status=HealthStatus.UNHEALTHY,
                health_message="door is OFFLINE",
            )
        return DoorHealth(
            id_=state.door_name,
            health_status=HealthStatus.UNHEALTHY,
            health_message="door is in an unknown mode",
        )

    async def _watch_door_health(self):
        def to_door_health(id_: str, has_heartbeat: bool):
            if has_heartbeat:
                return DoorHealth(id_=id_, health_status=HealthStatus.HEALTHY)
            return DoorHealth(
                id_=id_,
                health_status=HealthStatus.DEAD,
                health_message="heartbeat failed",
            )

        def watch(id_: str, obs: Observable):
            door_mode_health = obs.pipe(
                ops.map(cast(Any, self.door_mode_to_health)),
                ops.distinct_until_changed(),
            )
            obs.pipe(
                heartbeat(self.LIVELINESS),
                ops.map(
                    cast(Any, lambda has_heartbeat: to_door_health(id_, has_heartbeat))
                ),
                self._combine_most_critical(door_mode_health),
            ).subscribe(self.rmf.door_health.on_next, scheduler=self.scheduler)

        ttm_map = await ttm.BuildingMap.get_or_none()
        if ttm_map is None:
            doors = []
        else:
            building_map = BuildingMap.from_tortoise(ttm_map)
            doors = [door for level in building_map.levels for door in level.doors]
        states_list = [DoorState.from_tortoise(x) for x in await ttm.DoorState.all()]
        door_states = {state.door_name: state for state in states_list}
        initial_states = {door.name: door_states.get(door.name, None) for door in doors}

        subjects: Dict[str, BehaviorSubject] = {
            id_: BehaviorSubject(state) for id_, state in initial_states.items()
        }
        for id_, subject in subjects.items():
            watch(id_, subject)

        def on_state(state: DoorState):
            if state.door_name not in subjects:
                subjects[state.door_name] = BehaviorSubject(state)
                watch(state.door_name, subjects[state.door_name])
            else:
                subjects[state.door_name].on_next(state)

        self.rmf.door_states.subscribe(on_state)

    @staticmethod
    def lift_mode_to_health(state: Optional[LiftState]):
        if state is None:
            return None

        if state.current_mode in (
            RmfLiftState.MODE_HUMAN,
            RmfLiftState.MODE_AGV,
        ):
            return LiftHealth(
                id_=state.lift_name,
                health_status=HealthStatus.HEALTHY,
            )
        if state.current_mode == RmfLiftState.MODE_FIRE:
            return LiftHealth(
                id_=state.lift_name,
                health_status=HealthStatus.UNHEALTHY,
                health_message="lift is in FIRE mode",
            )
        if state.current_mode == RmfLiftState.MODE_EMERGENCY:
            return LiftHealth(
                id_=state.lift_name,
                health_status=HealthStatus.UNHEALTHY,
                health_message="lift is in EMERGENCY mode",
            )
        return LiftHealth(
            id_=state.lift_name,
            health_status=HealthStatus.UNHEALTHY,
            health_message="lift is in an unknown mode",
        )

    async def _watch_lift_health(self):
        def to_lift_health(id_: str, has_heartbeat: bool):
            if has_heartbeat:
                return LiftHealth(id_=id_, health_status=HealthStatus.HEALTHY)
            return LiftHealth(
                id_=id_,
                health_status=HealthStatus.DEAD,
                health_message="heartbeat failed",
            )

        def watch(id_: str, obs: Observable):
            lift_mode_health = obs.pipe(
                ops.map(cast(Any, self.lift_mode_to_health)),
                ops.distinct_until_changed(),
            )
            obs.pipe(
                heartbeat(self.LIVELINESS),
                ops.map(
                    cast(Any, lambda has_heartbeat: to_lift_health(id_, has_heartbeat))
                ),
                self._combine_most_critical(lift_mode_health),
            ).subscribe(self.rmf.lift_health.on_next, scheduler=self.scheduler)

        ttm_map = await ttm.BuildingMap.get_or_none()
        if ttm_map is None:
            lifts = []
        else:
            building_map = BuildingMap.from_tortoise(ttm_map)
            lifts = building_map.lifts
        states_list = [LiftState.from_tortoise(x) for x in await ttm.LiftState.all()]
        lift_states = {state.lift_name: state for state in states_list}
        initial_states = {lift.name: lift_states.get(lift.name, None) for lift in lifts}

        subjects: Dict[str, BehaviorSubject] = {
            id_: BehaviorSubject(state) for id_, state in initial_states.items()
        }
        for id_, subject in subjects.items():
            watch(id_, subject)

        def on_state(state: LiftState):
            if state.lift_name not in subjects:
                subjects[state.lift_name] = BehaviorSubject(state)
                watch(state.lift_name, subjects[state.lift_name])
            else:
                subjects[state.lift_name].on_next(state)

        self.rmf.lift_states.subscribe(on_state)

    @staticmethod
    def dispenser_mode_to_health(state: Optional[DispenserState]):
        if state is None:
            return None
        if state.mode in (
            RmfDispenserState.IDLE,
            RmfDispenserState.BUSY,
        ):
            return DispenserHealth(
                id_=state.guid,
                health_status=HealthStatus.HEALTHY,
            )
        if state.mode == RmfDispenserState.OFFLINE:
            return DispenserHealth(
                id_=state.guid,
                health_status=HealthStatus.UNHEALTHY,
                health_message="dispenser is OFFLINE",
            )
        return DispenserHealth(
            id_=state.guid,
            health_status=HealthStatus.UNHEALTHY,
            health_message="dispenser is in an unknown mode",
        )

    async def _watch_dispenser_health(self):
        def to_dispenser_health(id_: str, has_heartbeat: bool):
            if has_heartbeat:
                return DispenserHealth(id_=id_, health_status=HealthStatus.HEALTHY)
            return DispenserHealth(
                id_=id_,
                health_status=HealthStatus.DEAD,
                health_message="heartbeat failed",
            )

        def watch(id_: str, obs: Observable):
            dispenser_mode_health = obs.pipe(
                ops.map(cast(Any, self.dispenser_mode_to_health)),
                ops.distinct_until_changed(),
            )
            obs.pipe(
                heartbeat(self.LIVELINESS),
                ops.map(
                    cast(
                        Any,
                        lambda has_heartbeat: to_dispenser_health(id_, has_heartbeat),
                    )
                ),
                self._combine_most_critical(dispenser_mode_health),
            ).subscribe(self.rmf.dispenser_health.on_next, scheduler=self.scheduler)

        states_list = [
            DispenserState.from_tortoise(x) for x in await ttm.DispenserState.all()
        ]
        dispensers = [Dispenser(guid=x.guid) for x in states_list]
        dispenser_states = {state.guid: state for state in states_list}
        initial_states = {
            dispenser.guid: dispenser_states.get(dispenser.guid, None)
            for dispenser in dispensers
        }

        subjects: Dict[str, BehaviorSubject] = {
            id_: BehaviorSubject(state) for id_, state in initial_states.items()
        }
        for id_, subject in subjects.items():
            watch(id_, subject)

        def on_state(state: DispenserState):
            if state.guid not in subjects:
                subjects[state.guid] = BehaviorSubject(state)
                watch(state.guid, subjects[state.guid])
            else:
                subjects[state.guid].on_next(state)

        self.rmf.dispenser_states.subscribe(on_state)

    @staticmethod
    def ingestor_mode_to_health(state: IngestorState):
        if state.mode in (
            RmfIngestorState.IDLE,
            RmfIngestorState.BUSY,
        ):
            return IngestorHealth(
                id_=state.guid,
                health_status=HealthStatus.HEALTHY,
            )
        if state.mode == RmfIngestorState.OFFLINE:
            return IngestorHealth(
                id_=state.guid,
                health_status=HealthStatus.UNHEALTHY,
                health_message="ingestor is OFFLINE",
            )
        return IngestorHealth(
            id_=state.guid,
            health_status=HealthStatus.UNHEALTHY,
            health_message="ingestor is in an unknown mode",
        )

    async def _watch_ingestor_health(self):
        def to_ingestor_health(id_: str, has_heartbeat: bool):
            if has_heartbeat:
                return IngestorHealth(id_=id_, health_status=HealthStatus.HEALTHY)
            return IngestorHealth(
                id_=id_,
                health_status=HealthStatus.DEAD,
                health_message="heartbeat failed",
            )

        def watch(id_: str, obs: Observable):
            ingestor_mode_health = obs.pipe(
                ops.map(cast(Any, self.ingestor_mode_to_health)),
                ops.distinct_until_changed(),
            )
            obs.pipe(
                heartbeat(self.LIVELINESS),
                ops.map(
                    cast(
                        Any,
                        lambda has_heartbeat: to_ingestor_health(id_, has_heartbeat),
                    )
                ),
                self._combine_most_critical(ingestor_mode_health),
            ).subscribe(self.rmf.ingestor_health.on_next, scheduler=self.scheduler)

        states_list = [
            IngestorState.from_tortoise(x) for x in await ttm.IngestorState.all()
        ]
        ingestors = [Ingestor(guid=x.guid) for x in states_list]
        ingestor_states = {state.guid: state for state in states_list}
        initial_states = {
            ingestor.guid: ingestor_states.get(ingestor.guid, None)
            for ingestor in ingestors
        }

        subjects: Dict[str, BehaviorSubject] = {
            id_: BehaviorSubject(state) for id_, state in initial_states.items()
        }
        for id_, subject in subjects.items():
            watch(id_, subject)

        def on_state(state: IngestorState):
            if state.guid not in subjects:
                subjects[state.guid] = BehaviorSubject(state)
                watch(state.guid, subjects[state.guid])
            else:
                subjects[state.guid].on_next(state)

        self.rmf.ingestor_states.subscribe(on_state)

    @staticmethod
    def robot_mode_to_health(id_: Optional[str], state: Optional[RobotState]):
        if id_ is None or state is None:
            return None

        if state.mode.mode in (
            RmfRobotMode.MODE_IDLE,
            RmfRobotMode.MODE_CHARGING,
            RmfRobotMode.MODE_MOVING,
            RmfRobotMode.MODE_PAUSED,
            RmfRobotMode.MODE_WAITING,
            RmfRobotMode.MODE_GOING_HOME,
            RmfRobotMode.MODE_DOCKING,
        ):
            return RobotHealth(
                id_=id_,
                health_status=HealthStatus.HEALTHY,
            )
        if state.mode.mode == RmfRobotMode.MODE_EMERGENCY:
            return RobotHealth(
                id_=id_,
                health_status=HealthStatus.UNHEALTHY,
                health_message="robot is in EMERGENCY mode",
            )
        if state.mode.mode == RmfRobotMode.MODE_ADAPTER_ERROR:
            return RobotHealth(
                id_=id_,
                health_status=HealthStatus.UNHEALTHY,
                health_message="error in fleet adapter",
            )
        return RobotHealth(
            id_=id_,
            health_status=HealthStatus.UNHEALTHY,
            health_message="robot is in an unknown mode",
        )

    async def _watch_robot_health(self):
        def to_robot_health(id_: str, has_heartbeat: bool):
            if has_heartbeat:
                return RobotHealth(
                    id_=id_,
                    health_status=HealthStatus.HEALTHY,
                )
            return RobotHealth(
                id_=id_,
                health_status=HealthStatus.DEAD,
                health_message="heartbeat failed",
            )

        def watch(id_: str, obs: Observable):
            """
            :param obs: Observable[RobotState]
            """
            robot_mode_health = obs.pipe(
                ops.map(cast(Any, lambda state: self.robot_mode_to_health(id_, state))),
                ops.distinct_until_changed(),
            )
            obs.pipe(
                heartbeat(self.LIVELINESS),
                ops.map(cast(Any, lambda x: to_robot_health(id_, x))),
                self._combine_most_critical(robot_mode_health),
            ).subscribe(self.rmf.robot_health.on_next, scheduler=self.scheduler)

        fleet_states = [FleetState.from_tortoise(x) for x in await ttm.FleetState.all()]
        initial_states = {s.name: s for s in fleet_states}

        subjects: Dict[str, BehaviorSubject] = {}
        for fleet_state in initial_states.values():
            fleet_state: FleetState
            for robot_state in fleet_state.robots:
                robot_state: RobotState
                robot_id = f"{fleet_state.name}/{robot_state.name}"
                subjects[robot_id] = BehaviorSubject(None)

        for id_, subject in subjects.items():
            watch(id_, subject)

        def on_state(fleet_state: FleetState):
            for robot_state in fleet_state.robots:
                robot_state: RobotState
                robot_id = f"{fleet_state.name}/{robot_state.name}"

                if robot_id not in subjects:
                    subjects[robot_id] = BehaviorSubject(robot_state)
                    watch(robot_id, subjects[robot_id])
                else:
                    subjects[robot_id].on_next(robot_state)

        self.rmf.fleet_states.subscribe(on_state)
