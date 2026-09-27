import axios from "axios";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

import {
  Attendee,
  Coordinator,
  Event,
  NotifyResponse,
  PersonalCheckIn,
  PublicEvent,
  QRResponse,
  TokenResponse,
} from "./types";

// Android emulator uses 10.0.2.2 to reach the host machine.
// For a physical phone, set EXPO_PUBLIC_API_URL to your computer's LAN address.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://10.0.2.2:8000";

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
    if (error.message) return error.message;
  }
  return "Something went wrong. Please try again.";
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/api/auth/login", { email, password });
  await writeToken(data.access_token);
  return data;
}

export async function register(name: string, email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/api/auth/register", { name, email, password });
  await writeToken(data.access_token);
  return data;
}

export async function getMe(): Promise<Coordinator> {
  const { data } = await client.get<Coordinator>("/api/auth/me");
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

export async function registerDevice(attendeeId: number, fcmToken: string, platform: "android" | "ios") {
  await client.post(`/api/checkin/register-device/${attendeeId}`, {
    fcm_token: fcmToken,
    platform,
  });
}

export async function logout() {
  await clearToken();
}

export async function hasAccessToken(): Promise<boolean> {
  return Boolean(await readToken());
}
