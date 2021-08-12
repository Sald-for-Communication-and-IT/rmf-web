import React from 'react';
import { DefaultReportQueryPayload, defaultReportStyles } from '../default-report-interface';
import { DefaultDatesForm } from '../default-dates-form';
import { TaskSummaryReportTable, TaskSummaryRowsType } from './task-summary-report-table';
import { ReportConfigProps } from '../utils';

export interface TaskSummaryReportProps extends ReportConfigProps {
  getLogs: (data: DefaultReportQueryPayload) => Promise<TaskSummaryRowsType>;
}

export const TaskSummaryReport = (props: TaskSummaryReportProps): React.ReactElement => {
  const { getLogs, ...otherProps } = props;
  const [logs, setLogs] = React.useState<TaskSummaryRowsType>([]);
  const [lastSearchParams, setLastSearchParams] = React.useState<DefaultReportQueryPayload>({});

  const classes = defaultReportStyles();

  const searchLogs = async (payload: DefaultReportQueryPayload) => {
    setLastSearchParams(payload);
    setLogs(await getLogs(payload));
  };

  const getMoreLogs = async () => {
    setLogs(logs.concat(await getLogs({ ...lastSearchParams, offset: logs.length })));
  };

  return (
    <>
      <DefaultDatesForm search={searchLogs} {...otherProps} />
      <div className={classes.table}>
        {logs.length !== 0 && (
          <TaskSummaryReportTable rows={logs} tableSize={'48vh'} addMoreRows={getMoreLogs} />
        )}
      </div>
    </>
  );
};

export default TaskSummaryReport;