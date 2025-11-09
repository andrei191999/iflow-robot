// Match backend schema - flat structure
export interface UserSettings {
  uid?: string;
  iflowUrl?: string;
  iflowUsername?: string;
  iflowPassword?: string;
  iflowHeadless?: boolean;
  iflowTimeout?: number;
}

export interface TestCredentialsResponse {
  success: boolean;
  message?: string;
}
