import { makeStyles, Table, TableBody, TableCell, TableHead, TableRow } from '@material-ui/core';
import clsx from 'clsx';
import React from 'react';
import AutoSizer from 'react-virtualized-auto-sizer';
import { FixedSizeList, ListChildComponentProps } from 'react-window';
import { DispenserState as RmfDispenserState } from 'rmf-models';
import { Workcell, WorkcellState } from '.';
import { useFixedTableCellStyles } from '../utils';
import { dispenserModeToString } from './utils';

const useStyles = makeStyles((theme) => ({
  dispenserLabelIdle: {
    color: theme.palette.success.main,
  },
  dispenserLabelBusy: {
    color: theme.palette.error.main,
  },
  offlineLabelOffline: {
    color: theme.palette.warning.main,
  },
  tableRow: {
    display: 'flex',
    flexDirection: 'row',
  },
  tableCell: {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
}));

export interface WorkcellTableProps {
  workcells: Workcell[];
  workcellStates: Record<string, WorkcellState>;
}

interface WorkcellListRendererProps extends ListChildComponentProps {
  data: WorkcellTableProps;
}

export interface WorkcellRowProps {
  workcell: Workcell;
  mode?: number;
  requestGuidQueue?: string[];
  secondsRemaining?: number;
}

const WorkcellRow = React.memo(
  ({ workcell, mode, requestGuidQueue, secondsRemaining }: WorkcellRowProps) => {
    const classes = useStyles();
    const { fixedTableCell } = useFixedTableCellStyles();
    const dispenserModeLabelClasses = React.useCallback(
      (mode: number): string => {
        switch (mode) {
          case RmfDispenserState.IDLE:
            return `${classes.dispenserLabelIdle}`;
          case RmfDispenserState.BUSY:
            return `${classes.dispenserLabelBusy}`;
          case RmfDispenserState.OFFLINE:
            return `${classes.offlineLabelOffline}`;
          default:
            return '';
        }
      },
      [classes],
    );

    return (
      <TableRow aria-label={`${workcell.guid}`} className={classes.tableRow} component="div">
        {mode !== undefined && requestGuidQueue !== undefined && secondsRemaining !== undefined ? (
          <React.Fragment>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
              title={workcell.guid}
            >
              {workcell.guid}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(dispenserModeLabelClasses(mode), classes.tableCell, fixedTableCell)}
            >
              {dispenserModeToString(mode)}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
            >
              {requestGuidQueue.length}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
            >
              {requestGuidQueue}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
            >
              {secondsRemaining}
            </TableCell>
          </React.Fragment>
        ) : (
          <React.Fragment>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
              title={workcell.guid}
            >
              {workcell.guid}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
            >
              {'NA'}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
            >
              {'NA'}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
            >
              {'NA'}
            </TableCell>
            <TableCell
              component="div"
              variant="head"
              className={clsx(classes.tableCell, fixedTableCell)}
            >
              {'NA'}
            </TableCell>
          </React.Fragment>
        )}
      </TableRow>
    );
  },
);

const WorkcellListRenderer = ({ data, index }: WorkcellListRendererProps) => {
  const workcell = data.workcells[index];
  const workcellState: WorkcellState | undefined = data.workcellStates[workcell.guid];

  return (
    <WorkcellRow
      workcell={workcell}
      mode={workcellState?.mode}
      requestGuidQueue={workcellState?.request_guid_queue}
      secondsRemaining={workcellState?.seconds_remaining}
    />
  );
};

export const WorkcellTable = ({ workcells, workcellStates }: WorkcellTableProps): JSX.Element => {
  const classes = useStyles();
  const { fixedTableCell } = useFixedTableCellStyles();
  return (
    <AutoSizer disableHeight>
      {({ width }) => {
        return (
          <Table component="div" stickyHeader size="small" aria-label="workcell-table">
            <TableHead component="div">
              <TableRow component="div" className={classes.tableRow}>
                <TableCell
                  component="div"
                  variant="head"
                  className={clsx(classes.tableCell, fixedTableCell)}
                >
                  Dispenser Name
                </TableCell>
                <TableCell
                  component="div"
                  variant="head"
                  className={clsx(classes.tableCell, fixedTableCell)}
                >
                  Op. Mode
                </TableCell>
                <TableCell
                  component="div"
                  variant="head"
                  className={clsx(classes.tableCell, fixedTableCell)}
                >
                  No. Queued Requests
                </TableCell>
                <TableCell
                  component="div"
                  variant="head"
                  className={clsx(classes.tableCell, fixedTableCell)}
                >
                  Request Queue ID
                </TableCell>
                <TableCell
                  component="div"
                  variant="head"
                  className={clsx(classes.tableCell, fixedTableCell)}
                >
                  Seconds Remaining
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody component="div">
              <FixedSizeList
                itemSize={43}
                itemCount={workcells.length}
                height={200}
                width={width}
                itemData={{
                  workcells,
                  workcellStates,
                  width,
                }}
              >
                {WorkcellListRenderer}
              </FixedSizeList>
            </TableBody>
          </Table>
        );
      }}
    </AutoSizer>
  );
};
