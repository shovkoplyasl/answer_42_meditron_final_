let csrf = '';
export async function request<T>(path: string, data?: unknown, method = 'POST'): Promise<T> {
  const multipart = data instanceof FormData;
  const response = await fetch(path, { method: data === undefined ? 'GET' : method, credentials: 'same-origin',
    headers: data === undefined ? {} : { ...(multipart ? {} : {'Content-Type': 'application/json'}), 'X-CSRF-Token': csrf },
    body: data === undefined ? undefined : multipart ? data : JSON.stringify(data) });
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/auth/login') window.dispatchEvent(new Event('session-expired'));
    const detail = result.error || result.detail;
    throw new Error(typeof detail === 'string' ? detail : 'Проверьте заполнение полей');
  }
  if (result.csrf) csrf = result.csrf;
  return result as T;
}
export interface User { username: string; name: string; role: string }
export interface Session { user: User | null; csrf?: string }
export interface HighlightComment { id: string; text: string; comment: string }
export interface Patient {
  id: string; patientId: number; protocolId: number; routeId: number | null;
  routes: {id: number; specialist: string; status: string}[];
  fio: string; gender: string; birthDate: string; attendingDoctorFio: string; attendingDoctorSpec: string;
  protocolDate: string; protocolDateISO: string; fileName: string | null; routeDate: string; humanInterference: boolean;
  pushCount: number; targetDoctorSpec: string; csScore: number | null; aiComment: string; protocolFullText: string;
  highlights: HighlightComment[]; stage: string; status: string; urgency: string; city: string; canNotify: boolean;
}
