export interface ApiErrorResponse {
  error: string;
  code: string;
  upgrade_url?: string;
}

export class ApiClientError extends Error {
  code: string;
  status: number;
  upgradeUrl?: string;

  constructor(status: number, message: string, code: string, upgradeUrl?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.upgradeUrl = upgradeUrl;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${baseUrl}${endpoint}`;

  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const defaultHeaders: Record<string, string> = isFormData
    ? {}
    : { "Content-Type": "application/json" };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorData: ApiErrorResponse;
    try {
      errorData = (await response.json()) as ApiErrorResponse;
    } catch {
      errorData = {
        error: "Неизвестная ошибка сервера",
        code: "UNKNOWN_ERROR",
      };
    }
    throw new ApiClientError(
      response.status,
      errorData.error || "Ошибка запроса",
      errorData.code || "REQUEST_FAILED",
      errorData.upgrade_url
    );
  }

  return response.json() as Promise<T>;
}
