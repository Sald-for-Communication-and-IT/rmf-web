import {
  Box,
  BoxProps,
  Grid,
  makeStyles,
  Theme,
  Tooltip,
  Typography,
  useTheme,
} from '@material-ui/core';
import type { TaskSummary } from 'api-client';
import clsx from 'clsx';
import React from 'react';
import { TaskSummary as RmfTaskSummary } from 'rmf-models';

const getPhaseColors = (theme: Theme) => ({
  pending: theme.palette.info.light,
  completed: theme.palette.success.light,
  failed: theme.palette.error.light,
});

const useStyles = makeStyles((theme) => {
  const phaseColors = getPhaseColors(theme);
  return {
    taskPhasesContainer: {
      overflowX: 'auto',
    },
    taskPhase: {
      padding: theme.spacing(1),
      borderRadius: theme.shape.borderRadius,
      flex: '1 1 0',
      minWidth: 100,
    },
    pendingPhase: {
      background: phaseColors.pending,
    },
    completedPhase: {
      background: phaseColors.completed,
    },
    failedPhase: {
      background: phaseColors.failed,
    },
    phaseSeparator: {
      position: 'relative',
      left: theme.spacing(-1),
      margin: `0 ${theme.spacing(-2)}px 0 0`,
    },
    phaseStatus: {
      textOverflow: 'ellipsis',
      overflow: 'hidden',
      whiteSpace: 'nowrap',
    },
  };
});

interface PhaseProps extends React.HTMLProps<HTMLDivElement> {
  status: string;
}

function Phase({ status, ...divProps }: PhaseProps) {
  const classes = useStyles();
  const lines = status.split('\n');
  return (
    <div {...divProps}>
      {lines.map((l, idx) => (
        <Tooltip key={idx} title={l}>
          <Typography key={idx} className={classes.phaseStatus} variant="caption">
            {l}
          </Typography>
        </Tooltip>
      ))}
    </div>
  );
}

interface PhaseSeparatorProps {
  leftColor: string;
  rightColor: string;
}

function PhaseSeparator({ leftColor, rightColor }: PhaseSeparatorProps) {
  const classes = useStyles();
  return (
    <div className={classes.phaseSeparator}>
      <svg viewBox="-0.05 -0.05 1.1 1.1" width="50px" height="100%" preserveAspectRatio="none">
        <polygon
          points="0,0 0.1,0 0.4,0.5, 0.1,1 0,1"
          strokeLinejoin="round"
          strokeWidth={0.1}
          stroke={leftColor}
          fill={leftColor}
        />
        <polygon
          points="0.4,0 1,0, 1,1 0.4,1 0.7,0.5"
          strokeLinejoin="round"
          strokeWidth={0.1}
          stroke={rightColor}
          fill={rightColor}
        />
      </svg>
    </div>
  );
}

export interface TaskPhasesProps extends BoxProps {
  taskSummary: TaskSummary;
}

export function TaskPhases({ taskSummary, ...boxProps }: TaskPhasesProps): JSX.Element {
  const classes = useStyles();
  const theme = useTheme();
  const phaseColors = getPhaseColors(theme);

  const phases = taskSummary.status.split('\n\n');
  const currentPhaseIdx = phases.findIndex((msg) => msg.startsWith('*'));
  // probably don't need to memo for now because almost all renders will change its
  // dependencies.
  const phaseProps = phases.map((_, idx) => {
    if ([RmfTaskSummary.STATE_CANCELED, RmfTaskSummary.STATE_FAILED].includes(taskSummary.state)) {
      return {
        className: classes.failedPhase,
        color: phaseColors.failed,
      };
    }

    if (taskSummary.state === RmfTaskSummary.STATE_COMPLETED) {
      return {
        className: classes.completedPhase,
        color: phaseColors.completed,
      };
    }

    if (taskSummary.state === RmfTaskSummary.STATE_ACTIVE && idx < currentPhaseIdx) {
      return {
        className: classes.completedPhase,
        color: phaseColors.completed,
      };
    }

    return {
      className: classes.pendingPhase,
      color: phaseColors.pending,
    };
  });

  return (
    <Box {...boxProps}>
      <Grid container={true} wrap="nowrap" className={classes.taskPhasesContainer}>
        {phases.map((phase, idx) => (
          <React.Fragment key={idx}>
            <Phase status={phase} className={clsx(classes.taskPhase, phaseProps[idx].className)} />
            {idx != phases.length - 1 && (
              <PhaseSeparator
                leftColor={phaseProps[idx].color}
                rightColor={phaseProps[idx + 1].color}
              />
            )}
          </React.Fragment>
        ))}
      </Grid>
    </Box>
  );
}
