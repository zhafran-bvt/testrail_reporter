import { AppConfig } from "./types";

export const appConfig: AppConfig = (window as any).__APP_CONFIG__ || {};
