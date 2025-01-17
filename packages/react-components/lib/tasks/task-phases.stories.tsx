import { Meta, Story } from '@storybook/react';
import React from 'react';
import { TaskPhases, TaskPhasesProps } from './task-phases';
import { makeTaskSummaryWithPhases } from './test-data.spec';

const task = makeTaskSummaryWithPhases('test_task', 3, 3);

export default {
  title: 'Tasks/Phases',
  component: TaskPhases,
} as Meta;

export const Phases: Story<TaskPhasesProps> = (args) => {
  return <TaskPhases {...args}></TaskPhases>;
};

Phases.args = {
  taskSummary: task,
};
