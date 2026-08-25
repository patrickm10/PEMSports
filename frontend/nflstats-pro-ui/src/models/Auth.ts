export interface UserProfile {
  id: string;
  email: string;
}

export interface SessionAck {
  ok: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
}

export class AuthApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'AuthApiError';
    this.status = status;
    this.detail = detail;
  }
}
