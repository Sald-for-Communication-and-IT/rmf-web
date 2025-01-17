/* istanbul ignore file */

import React from 'react';
import { RmfIngressContext } from '../rmf-app';
import { getApiErrorMessage } from '../utils';
import { usePageStyles } from './page-css';
import { UserListCard } from './user-list-card';

export function UserListPage(): JSX.Element | null {
  const classes = usePageStyles();
  const rmfIngress = React.useContext(RmfIngressContext);
  const adminApi = rmfIngress?.adminApi;

  if (!adminApi) return null;

  return (
    <div className={classes.pageRoot}>
      <UserListCard
        searchUsers={async (search, limit, offset) => {
          try {
            return (await adminApi.getUsersAdminUsersGet(search, undefined, limit, offset)).data;
          } catch (e) {
            throw new Error(getApiErrorMessage(e));
          }
        }}
        deleteUser={async (user) => {
          try {
            await adminApi.deleteUserAdminUsersUsernameDelete(user);
          } catch (e) {
            throw new Error(getApiErrorMessage(e));
          }
        }}
        createUser={async (user) => {
          try {
            await adminApi.createUserAdminUsersPost({ username: user });
          } catch (e) {
            throw new Error(getApiErrorMessage(e));
          }
        }}
      />
    </div>
  );
}
