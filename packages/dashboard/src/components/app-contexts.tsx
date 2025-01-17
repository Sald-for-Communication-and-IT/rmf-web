import React from 'react';
import appConfig, { AppConfig } from '../app-config';
import ResourceManager from '../managers/resource-manager';
import { defaultSettings, Settings } from '../settings';

/* Declares the ResourcesContext which contains the resources used on the app*/
export const ResourcesContext = React.createContext<ResourceManager | undefined>(undefined);

export const SettingsContext = React.createContext(defaultSettings());

export interface AppController {
  setShowSettings: React.Dispatch<React.SetStateAction<boolean>>;
  updateSettings: (settings: Settings) => void;
  showHelp(show: boolean): void;
  toggleHelp(): void;
  showHotkeysDialog(show: boolean): void;
  toggleHotkeysDialog(): void;
  /**
   * FIXME: Move this to settings, this sets if we should show the tooltip icon, and not trigger
   * a tooltip to show.
   */
  showTooltips(show: boolean): void;
  /**
   * FIXME: Move this to settings, this sets if we should show the tooltip icon, and not trigger
   * a tooltip to show.
   */
  toggleTooltips(): void;
  showErrorAlert: (message: string, autoHideDuration?: number) => void;
}

export interface Tooltips {
  showTooltips: boolean;
}

export const TooltipsContext = React.createContext<Tooltips>({
  showTooltips: true,
});

export const AppControllerContext = React.createContext<AppController>({
  setShowSettings: () => {},
  updateSettings: () => {},
  showHelp: () => {},
  toggleHelp: () => {},
  showHotkeysDialog: () => {},
  toggleHotkeysDialog: () => {},
  showTooltips: () => {},
  toggleTooltips: () => {},
  showErrorAlert: () => {},
});

export const AppConfigContext = React.createContext<AppConfig>(appConfig);
