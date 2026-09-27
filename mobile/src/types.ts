export type EventStatus = "draft" | "active" | "completed";
export type CheckInStatus = "pending" | "checked_in";

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type Coordinator = {
  id: number;
  name: string;
  email: string;
};

export type Event = {
  id: number;
  title: string;
  description: string | null;
  location: string | null;
  start_time: string;
  end_time: string | null;
  coordinator_id: number;
  status: EventStatus;
  qr_token: string;
  created_at: string;
  attendee_count: number;
  checked_in_count: number;
};

export type Attendee = {
  id: number;
  event_id: number;
  full_name: string;
  email: string | null;
  phone: string | null;
  student_id: string | null;
  check_in_status: CheckInStatus;
  checked_in_at: string | null;
  has_device_token: boolean;
};

export type PublicEvent = {
  id: number;
  title: string;
  description: string | null;
  location: string | null;
  start_time: string;
  end_time: string | null;
  status: EventStatus;
  attendees: Attendee[];
};

export type QRResponse = {
  qr_token: string;
  qr_base64: string;
  checkin_url: string;
};

export type PersonalCheckIn = {
  event_id: number;
  event_title: string;
  attendee: Attendee;
};

export type NotifyResponse = {
  recipient_count: number;
  push_count: number;
  email_count: number;
  message: string;
};
