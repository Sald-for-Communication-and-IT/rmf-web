import { makeStyles } from '@material-ui/core';
import { Meta, Story } from '@storybook/react';
import React from 'react';
import { ErrorOverlay } from './error-overlay';
import { SimpleInfo } from './simple-info';

export default {
  title: 'Error Overlay',
  component: ErrorOverlay,
} as Meta;

// override style with userSelect disabled
const useStyles = makeStyles(() => ({
  container: {
    display: 'table',
    borderCollapse: 'collapse',
    width: '100%',
    overflowX: 'auto',
    userSelect: 'none',
  },
}));

function TestComponent() {
  const classes = useStyles();
  const data = [
    { name: 'String', value: 'This is a string' },
    { name: 'Number', value: 3 },
    {
      name: 'Array',
      value: ['one', 'two', 'three'],
    },
  ];
  return <SimpleInfo infoData={data} overrideStyle={classes} />;
}

export const ErrorOverlayPanel: Story = (args) => {
  return (
    <>
      <ErrorOverlay errorMsg={'This is an error message'} {...args}>
        <TestComponent />
      </ErrorOverlay>
    </>
  );
};
