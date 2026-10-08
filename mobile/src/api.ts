import axios from "axios";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

import {
  Attendee,
  AttendeeAccount,
  AdminCoordinator,
  AdminStudent,
  Coordinator,
  Event,
  NotifyResponse,
  PersonalCheckIn,
  PublicEvent,
  QRResponse,
  TokenResponse,
} from "./types";

// Android emulator uses 10.0.2.2 to reach the host machine. iOS simulators,
// web, and desktop development use localhost. For a physical phone, set
// EXPO_PUBLIC_API_URL to the computer's LAN address.
const defaultApiUrl = Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://127.0.0.1:8000";
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? defaultApiUrl;
const SESSION_TYPE_KEY = "session_type";

async function readToken(): Promise<string | null> {
  if (Platform.OS === "web") return typeof localStorage === "undefined" ? null : localStorage.getItem("access_token");
  return SecureStore.getItemAsync("access_token");
}

async function writeToken(token: string): Promise<void> {
  if (Platform.OS === "web") {
    localStorage.setItem("access_token", token);
    return;
  }
  await SecureStore.setItemAsync("access_token", token);
}

async function clearToken(): Promise<void> {
  if (Platform.OS === "web") {
    localStorage.removeItem("access_token");
    return;
  }
  await SecureStore.deleteItemAsync("access_token");
}

const client = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use(async (config) => {
  const token = await readToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function apiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (!error.response) return "Cannot reach the server. Check that the backend is running and your phone is on the same network.";
    if (error.response.status === 401) return "Your session has expired. Please log in again.";
    if (error.response.status === 403) return "You do not have permission to access this record.";
    if (error.response.status === 404) return "The requested record was not found.";
    if (error.response.status === 422) return "Please check the information you entered and try again.";
    if (error.response.status === 409) return "This action has already been completed or conflicts with existing data.";
    if (error.response.status >= 500) return "The server or database is temporarily unavailable. Please try again.";
    if (error.message) return error.message;
  }
  return "Something went wrong. Please try again.";
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/api/auth/login", { email, password });
  await writeToken(data.access_token);
  await writeSessionType("host");
  return data;
}

export async function register(name: string, email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/api/auth/register", { name, email, password });
  await writeToken(data.access_token);
  await writeSessionType("host");
  return data;
}

export async function loginAttendee(email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/api/auth/attendee/login", { email, password });
  await writeToken(data.access_token);
  await writeSessionType("attendee");
  return data;
}

export async function loginWithGoogle(idToken: string, accountType: "host" | "attendee"): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/api/auth/google", {
    id_token: idToken,
    account_type: accountType,
  });
  await writeToken(data.access_token);
  await writeSessionType(accountType);
  return data;
}

export async function registerAttendee(fullName: string, email: string, studentId: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/api/auth/attendee/register", {
    full_name: fullName,
    email,
    student_id: studentId,
    password,
  });
  await writeToken(data.access_token);
  await writeSessionType("attendee");
  return data;
}

export async function getMe(): Promise<Coordinator> {
  const { data } = await client.get<Coordinator>("/api/auth/me");
  return data;
}

export async function getAttendeeMe(): Promise<AttendeeAccount> {
  const { data } = await client.get<AttendeeAccount>("/api/auth/attendee/me");
  return data;
}

export async function getAttendeeAccountQR(): Promise<QRResponse> {
  const { data } = await client.get<QRResponse>("/api/auth/attendee/qr");
  return data;
}

export async function listAdminCoordinators(): Promise<AdminCoordinator[]> {
  const { data } = await client.get<AdminCoordinator[]>("/api/admin/coordinators");
  return data;
}

export async function createAdminHost(name: string, email: string, password: string): Promise<AdminCoordinator> {
  const { data } = await client.post<AdminCoordinator>("/api/admin/coordinators", { name, email, password });
  return data;
}

export async function setAdminCoordinatorStatus(id: number, isActive: boolean): Promise<AdminCoordinator> {
  const { data } = await client.patch<AdminCoordinator>(`/api/admin/coordinators/${id}/status`, { is_active: isActive });
  return data;
}

export async function listAdminStudents(): Promise<AdminStudent[]> {
  const { data } = await client.get<AdminStudent[]>("/api/admin/students");
  return data;
}

export async function setAdminStudentStatus(id: number, isActive: boolean): Promise<AdminStudent> {
  const { data } = await client.patch<AdminStudent>(`/api/admin/students/${id}/status`, { is_active: isActive });
  return data;
}

export async function listEvents(): Promise<Event[]> {
  const { data } = await client.get<Event[]>("/api/events");
  return data;
}

export async function createEvent(input: {
  title: string;
  description?: string;
  location?: string;
  start_time: string;
  end_time?: string;
}): Promise<Event> {
  const { data } = await client.post<Event>("/api/events", input);
  return data;
}

export async function getEvent(eventId: number): Promise<Event> {
  const { data } = await client.get<Event>(`/api/events/${eventId}`);
  return data;
}

export async function listAttendees(eventId: number): Promise<Attendee[]> {
  const { data } = await client.get<Attendee[]>(`/api/events/${eventId}/attendees`);
  return data;
}

export async function addAttendee(eventId: number, input: {
  full_name: string;
  email?: string;
  phone?: string;
  student_id?: string;
}): Promise<Attendee> {
  const { data } = await client.post<Attendee>(`/api/events/${eventId}/attendees`, input);
  return data;
}

export async function getQR(eventId: number): Promise<QRResponse> {
  const { data } = await client.get<QRResponse>(`/api/events/${eventId}/qr`);
  return data;
}

export async function getAttendeeQR(eventId: number, attendeeId: number): Promise<QRResponse> {
  const { data } = await client.get<QRResponse>(`/api/events/${eventId}/attendees/${attendeeId}/qr`);
  return data;
}

export async function notifyAll(eventId: number, message?: string): Promise<NotifyResponse> {
  const { data } = await client.post<NotifyResponse>(`/api/events/${eventId}/notify-all`, { message });
  return data;
}

export async function getPublicEvent(qrToken: string): Promise<PublicEvent> {
  const { data } = await client.get<PublicEvent>(`/api/checkin/${qrToken}`);
  return data;
}

export async function checkIn(qrToken: string, attendeeId: number): Promise<Attendee> {
  const { data } = await client.post<Attendee>(`/api/checkin/${qrToken}`, {
    attendee_id: attendeeId,
  });
  return data;
}

export async function getPersonalCheckIn(qrToken: string): Promise<PersonalCheckIn> {
  const { data } = await client.get<PersonalCheckIn>(`/api/checkin/attendee/${qrToken}`);
  return data;
}

export async function checkInPersonal(qrToken: string): Promise<Attendee> {
  const { data } = await client.post<Attendee>(`/api/checkin/attendee/${qrToken}`);
  return data;
}

export async function checkInAccount(eventId: number, qrToken: string): Promise<Attendee> {
  const { data } = await client.post<Attendee>(`/api/events/${eventId}/checkin/account/${encodeURIComponent(qrToken)}`);
  return data;
}

export async function registerDevice(attendeeId: number, fcmToken: string, platform: "android" | "ios") {
  await client.post(`/api/checkin/register-device/${attendeeId}`, {
    fcm_token: fcmToken,
    platform,
  });
}

export async function logout() {
  await clearToken();
  await clearSessionType();
}

export async function hasAccessToken(): Promise<boolean> {
  return Boolean(await readToken());
}

async function writeSessionType(value: "host" | "attendee"): Promise<void> {
  if (Platform.OS === "web") {
    localStorage.setItem(SESSION_TYPE_KEY, value);
    return;
  }
  await SecureStore.setItemAsync(SESSION_TYPE_KEY, value);
}

async function clearSessionType(): Promise<void> {
  if (Platform.OS === "web") {
    localStorage.removeItem(SESSION_TYPE_KEY);
    return;
  }
  await SecureStore.deleteItemAsync(SESSION_TYPE_KEY);
}

export async function getSessionType(): Promise<"host" | "attendee" | null> {
  if (Platform.OS === "web") {
    return (localStorage.getItem(SESSION_TYPE_KEY) as "host" | "attendee" | null) || null;
  }
  return (await SecureStore.getItemAsync(SESSION_TYPE_KEY)) as "host" | "attendee" | null;
}
