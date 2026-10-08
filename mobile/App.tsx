import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Notifications from "expo-notifications";
import * as WebBrowser from "expo-web-browser";
import * as Google from "expo-auth-session/providers/google";
import { ResponseType } from "expo-auth-session";
import { NavigationContainer } from "@react-navigation/native";
import { useFocusEffect } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import {
  addAttendee,
  apiError,
  checkIn,
  checkInAccount,
  createAdminHost,
  createEvent,
  checkInPersonal,
  getAttendeeQR,
  getAttendeeAccountQR,
  getAttendeeMe,
  getEvent,
  getMe,
  getPersonalCheckIn,
  getPublicEvent,
  getQR,
  getSessionType,
  hasAccessToken,
  listAttendees,
  listAdminCoordinators,
  listAdminStudents,
  listEvents,
  login,
  loginWithGoogle,
  loginAttendee,
  logout,
  notifyAll,
  register,
  registerAttendee,
  registerDevice,
  setAdminCoordinatorStatus,
  setAdminStudentStatus,
} from "./src/api";
import { AdminCoordinator, AdminStudent, Attendee, AttendeeAccount, Event, PersonalCheckIn, PublicEvent, QRResponse } from "./src/types";

WebBrowser.maybeCompleteAuthSession();

type RootStackParamList = {
  Login: undefined;
  Events: undefined;
  AdminHome: undefined;
  AttendeeHome: undefined;
  CreateEvent: undefined;
  EventDetail: { eventId: number };
  AddAttendee: { eventId: number };
  QRScanner: { eventId?: number } | undefined;
  CheckIn: { qrToken: string };
  PersonalCheckIn: { attendeeQrToken: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const colors = {
  ink: "#172033",
  muted: "#697386",
  primary: "#3157D5",
  background: "#F5F7FB",
  card: "#FFFFFF",
  border: "#E3E8F2",
  success: "#1C8C5A",
  danger: "#B42318",
};

function Screen({ children }: { children: React.ReactNode }) {
  return <SafeAreaView style={styles.safe}>{children}</SafeAreaView>;
}

function Button({ title, onPress, secondary = false }: { title: string; onPress: () => void; secondary?: boolean }) {
  return (
    <Pressable style={[styles.button, secondary && styles.secondaryButton]} onPress={onPress}>
      <Text style={[styles.buttonText, secondary && styles.secondaryButtonText]}>{title}</Text>
    </Pressable>
  );
}

function Field({ label, value, onChangeText, placeholder, secureTextEntry = false }: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
}) {
  return (
    <View style={styles.fieldGroup}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#9AA3B2"
        secureTextEntry={secureTextEntry}
        style={styles.input}
        autoCapitalize="none"
      />
    </View>
  );
}

function Loading() {
  return <ActivityIndicator style={styles.loading} size="large" color={colors.primary} />;
}

function LoginScreen({ navigation }: any) {
  const [accountType, setAccountType] = useState<"host" | "attendee">("host");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [studentId, setStudentId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleRequest, , promptGoogle] = Google.useAuthRequest({
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
    androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
    responseType: ResponseType.IdToken,
    scopes: ["openid", "profile", "email"],
  });

  async function submit() {
    if (!email || !password || (mode === "register" && (!name || (accountType === "attendee" && !studentId)))) {
      Alert.alert("Missing details", "Please complete all required fields.");
      return;
    }
    setBusy(true);
    try {
      if (accountType === "host") {
        if (mode === "login") {
          await login(email, password);
          const profile = await getMe();
          navigation.replace(profile.role === "admin" ? "AdminHome" : "Events");
        } else {
          await register(name, email, password);
          navigation.replace("Events");
        }
      } else {
        if (mode === "login") await loginAttendee(email, password);
        else await registerAttendee(name, email, studentId, password);
        navigation.replace("AttendeeHome");
      }
    } catch (error) {
      Alert.alert("Unable to continue", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  async function signInWithGoogle() {
    if (!googleRequest) {
      Alert.alert("Google Sign-In unavailable", "Add the Google client IDs to the mobile environment configuration first.");
      return;
    }
    setBusy(true);
    try {
      const result = await promptGoogle();
      if (result.type !== "success") return;
      const idToken = result.params?.id_token ?? (result as any).authentication?.idToken;
      if (!idToken) throw new Error("Google did not return an ID token.");
      await loginWithGoogle(idToken, accountType);
      if (accountType === "host") {
        const profile = await getMe();
        navigation.replace(profile.role === "admin" ? "AdminHome" : "Events");
      } else {
        navigation.replace("AttendeeHome");
      }
    } catch (error) {
      Alert.alert("Google Sign-In failed", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.authContainer} keyboardShouldPersistTaps="handled">
          <Text style={styles.brand}>QR Event</Text>
          <View style={styles.accountToggle}>
            <Pressable style={[styles.toggleOption, accountType === "host" && styles.toggleOptionActive]} onPress={() => { setAccountType("host"); setMode("login"); }}><Text style={styles.toggleText}>Host</Text></Pressable>
            <Pressable style={[styles.toggleOption, accountType === "attendee" && styles.toggleOptionActive]} onPress={() => { setAccountType("attendee"); setMode("login"); }}><Text style={styles.toggleText}>Student</Text></Pressable>
          </View>
          <Text style={styles.heroTitle}>{mode === "login" ? `${accountType === "host" ? "Host" : "Student"} login` : `Create ${accountType === "host" ? "a host" : "a student"} account`}</Text>
          <Text style={styles.subtitle}>{accountType === "host" ? "Manage events, rosters, check-ins, and notifications." : "Keep your student QR code ready for event check-in."}</Text>
          {mode === "register" && <Field label="Name" value={name} onChangeText={setName} placeholder="Your full name" />}
          {mode === "register" && accountType === "attendee" && <Field label="Student ID" value={studentId} onChangeText={setStudentId} placeholder="e.g. S2026-001" />}
          <Field label="Email" value={email} onChangeText={setEmail} placeholder="you@example.com" />
          <Field label="Password" value={password} onChangeText={setPassword} placeholder="At least 8 characters" secureTextEntry />
          {busy ? <Loading /> : <Button title={mode === "login" ? "Log in" : "Register"} onPress={submit} />}
          {mode === "login" && <Button title="Continue with Google" onPress={signInWithGoogle} secondary />}
          <Pressable onPress={() => setMode(mode === "login" ? "register" : "login")}>
            <Text style={styles.link}>{mode === "login" ? "Need an account? Register" : "Already registered? Log in"}</Text>
          </Pressable>
          <View style={styles.divider} />
          <Button title="Scan an event QR code" onPress={() => navigation.navigate("QRScanner")} secondary />
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}

function AdminHomeScreen({ navigation }: any) {
  const [hosts, setHosts] = useState<AdminCoordinator[]>([]);
  const [students, setStudents] = useState<AdminStudent[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(true);
  const [creating, setCreating] = useState(false);

  async function load() {
    setBusy(true);
    try {
      const [hostData, studentData] = await Promise.all([listAdminCoordinators(), listAdminStudents()]);
      setHosts(hostData);
      setStudents(studentData);
    } catch (error) {
      Alert.alert("Could not load administration data", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  useFocusEffect(useCallback(() => { load(); }, []));

  async function addHost() {
    if (!name || !email || !password) {
      Alert.alert("Missing details", "Enter the host's name, email, and password.");
      return;
    }
    setCreating(true);
    try {
      await createAdminHost(name, email, password);
      setName(""); setEmail(""); setPassword("");
      Alert.alert("Host created", "The host can now log in.");
      await load();
    } catch (error) {
      Alert.alert("Could not create host", apiError(error));
    } finally {
      setCreating(false);
    }
  }

  async function toggleHost(host: AdminCoordinator) {
    try { await setAdminCoordinatorStatus(host.id, !host.is_active); await load(); }
    catch (error) { Alert.alert("Could not update host", apiError(error)); }
  }

  async function toggleStudent(student: AdminStudent) {
    try { await setAdminStudentStatus(student.id, !student.is_active); await load(); }
    catch (error) { Alert.alert("Could not update student", apiError(error)); }
  }

  async function signOut() { await logout(); navigation.replace("Login"); }

  if (busy) return <Screen><Loading /></Screen>;
  return <Screen><ScrollView contentContainerStyle={styles.formContainer}>
    <View style={styles.headerRow}><View><Text style={styles.screenTitle}>Admin Center</Text><Text style={styles.subtitle}>Manage school accounts and access</Text></View><Pressable onPress={signOut}><Text style={styles.link}>Sign out</Text></Pressable></View>
    <View style={styles.adminSummary}><View style={styles.adminMetric}><Text style={styles.summaryNumber}>{hosts.length}</Text><Text style={styles.muted}>hosts</Text></View><View style={styles.adminMetric}><Text style={styles.summaryNumber}>{students.length}</Text><Text style={styles.muted}>students</Text></View></View>
    <Text style={styles.sectionTitle}>Create host account</Text>
    <Field label="Host name" value={name} onChangeText={setName} placeholder="Teacher or coordinator" />
    <Field label="Email" value={email} onChangeText={setEmail} placeholder="host@school.edu" />
    <Field label="Temporary password" value={password} onChangeText={setPassword} placeholder="At least 8 characters" secureTextEntry />
    {creating ? <Loading /> : <Button title="Create host" onPress={addHost} />}
    <Text style={styles.sectionTitle}>Hosts</Text>
    {hosts.map((host) => <View key={host.id} style={styles.adminRow}><View><Text style={styles.cardTitle}>{host.name}</Text><Text style={styles.muted}>{host.email} · {host.event_count} events</Text></View><Pressable onPress={() => toggleHost(host)}><Text style={[styles.status, host.is_active ? styles.checkedIn : styles.inactive]}>{host.is_active ? "Active" : "Inactive"}</Text></Pressable></View>)}
    <Text style={styles.sectionTitle}>Students</Text>
    {students.length === 0 ? <Text style={styles.empty}>No student accounts yet.</Text> : students.map((student) => <View key={student.id} style={styles.adminRow}><View><Text style={styles.cardTitle}>{student.full_name}</Text><Text style={styles.muted}>{student.student_id} · {student.event_count} events</Text></View><Pressable onPress={() => toggleStudent(student)}><Text style={[styles.status, student.is_active ? styles.checkedIn : styles.inactive]}>{student.is_active ? "Active" : "Inactive"}</Text></Pressable></View>)}
    <Button title="Refresh" onPress={load} secondary />
  </ScrollView></Screen>;
}

function AttendeeHomeScreen({ navigation }: any) {
  const [account, setAccount] = useState<AttendeeAccount | null>(null);
  const [qr, setQr] = useState<QRResponse | null>(null);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    Promise.all([getAttendeeMe(), getAttendeeAccountQR()])
      .then(([accountData, qrData]) => { setAccount(accountData); setQr(qrData); })
      .catch((error) => Alert.alert("Could not load student account", apiError(error)))
      .finally(() => setBusy(false));
  }, []);

  async function signOut() {
    await logout();
    navigation.replace("Login");
  }

  if (busy || !account || !qr) return <Screen><Loading /></Screen>;
  return <Screen><ScrollView contentContainerStyle={styles.formContainer}>
    <View style={styles.headerRow}><View><Text style={styles.screenTitle}>My student QR</Text><Text style={styles.subtitle}>{account.full_name}</Text></View><Pressable onPress={signOut}><Text style={styles.link}>Sign out</Text></Pressable></View>
    <View style={styles.summaryCard}><Text style={styles.cardTitle}>Student ID</Text><Text style={styles.summaryNumber}>{account.student_id}</Text></View>
    <View style={styles.qrCard}><Image source={{ uri: `data:image/png;base64,${qr.qr_base64}` }} style={styles.qr} /><Text style={styles.muted}>Show this QR code to a host at school events.</Text></View>
  </ScrollView></Screen>;
}

function EventsScreen({ navigation }: any) {
  const [events, setEvents] = useState<Event[]>([]);
  const [busy, setBusy] = useState(true);

  async function load(showLoading = true) {
    if (showLoading) setBusy(true);
    try {
      setEvents(await listEvents());
    } catch (error) {
      Alert.alert("Could not load events", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  useFocusEffect(useCallback(() => {
    load();
  }, []));

  async function signOut() {
    await logout();
    navigation.replace("Login");
  }

  return (
    <Screen>
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.screenTitle}>Event Book</Text>
          <Text style={styles.subtitle}>Your events</Text>
        </View>
        <Pressable onPress={signOut}><Text style={styles.link}>Sign out</Text></Pressable>
      </View>
      <View style={styles.actionRow}>
        <Button title="New event" onPress={() => navigation.navigate("CreateEvent")} />
        <Button title="Scan QR" onPress={() => navigation.navigate("QRScanner")} secondary />
      </View>
      {busy ? <Loading /> : (
        <FlatList
          data={events}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.listContent}
          refreshing={busy}
          onRefresh={load}
          ListEmptyComponent={<Text style={styles.empty}>No events yet. Create your first event.</Text>}
          renderItem={({ item }) => (
            <Pressable style={styles.card} onPress={() => navigation.navigate("EventDetail", { eventId: item.id })}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.badge}>{item.status}</Text>
              </View>
              <Text style={styles.muted}>{item.location || "No location"}</Text>
              <Text style={styles.muted}>{new Date(item.start_time).toLocaleString()}</Text>
              <Text style={styles.stats}>{item.checked_in_count}/{item.attendee_count} checked in</Text>
            </Pressable>
          )}
        />
      )}
    </Screen>
  );
}

function CreateEventScreen({ navigation }: any) {
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!title) {
      Alert.alert("Missing title", "Enter an event title first.");
      return;
    }
    setBusy(true);
    try {
      const event = await createEvent({
        title,
        location: location || undefined,
        description: description || undefined,
        start_time: new Date().toISOString(),
      });
      navigation.replace("EventDetail", { eventId: event.id });
    } catch (error) {
      Alert.alert("Could not create event", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.formContainer}>
        <Text style={styles.screenTitle}>Create event</Text>
        <Text style={styles.subtitle}>Start with the essentials. Date/time editing can be added next.</Text>
        <Field label="Title" value={title} onChangeText={setTitle} placeholder="e.g. Orientation Day" />
        <Field label="Location" value={location} onChangeText={setLocation} placeholder="e.g. Main Hall" />
        <Field label="Description" value={description} onChangeText={setDescription} placeholder="Optional details" />
        {busy ? <Loading /> : <Button title="Create event" onPress={submit} />}
      </ScrollView>
    </Screen>
  );
}

function EventDetailScreen({ route, navigation }: any) {
  const { eventId } = route.params as { eventId: number };
  const [event, setEvent] = useState<Event | null>(null);
  const [attendees, setAttendees] = useState<Attendee[]>([]);
  const [qr, setQr] = useState<QRResponse | null>(null);
  const [attendeeQR, setAttendeeQR] = useState<{ attendee: Attendee; qr: QRResponse } | null>(null);
  const [busy, setBusy] = useState(true);

  async function load(showLoading = true) {
    if (showLoading) setBusy(true);
    try {
      const [eventData, attendeesData] = await Promise.all([getEvent(eventId), listAttendees(eventId)]);
      setEvent(eventData);
      setAttendees(attendeesData);
    } catch (error) {
      Alert.alert("Could not load event", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  useFocusEffect(useCallback(() => {
    let active = true;
    load();
    const interval = setInterval(() => {
      if (active) load(false);
    }, 5000);
    return () => { active = false; clearInterval(interval); };
  }, [eventId]));

  async function showQR() {
    try {
      setQr(await getQR(eventId));
    } catch (error) {
      Alert.alert("Could not load QR code", apiError(error));
    }
  }

  async function sendNotification() {
    try {
      const result = await notifyAll(eventId);
      Alert.alert("Notification sent", result.message);
    } catch (error) {
      Alert.alert("Could not send notification", apiError(error));
    }
  }

  async function showAttendeeQR(attendee: Attendee) {
    try {
      setAttendeeQR({ attendee, qr: await getAttendeeQR(eventId, attendee.id) });
    } catch (error) {
      Alert.alert("Could not create attendee QR", apiError(error));
    }
  }

  if (busy || !event) return <Screen><Loading /></Screen>;

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.formContainer}>
        <Text style={styles.screenTitle}>{event.title}</Text>
        <Text style={styles.subtitle}>{event.location || "No location"} · Live updates every 5 seconds</Text>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryNumber}>{event.checked_in_count}/{event.attendee_count}</Text>
          <Text style={styles.muted}>checked in</Text>
        </View>
        <View style={styles.actionRow}>
          <Button title="Show event QR" onPress={showQR} />
          <Button title="Notify all" onPress={sendNotification} secondary />
        </View>
        <Button title="Scan student QR" onPress={() => navigation.navigate("QRScanner", { eventId })} secondary />
        <Button title="Add attendee" onPress={() => navigation.navigate("AddAttendee", { eventId })} secondary />
        {qr && <View style={styles.qrCard}><Image source={{ uri: `data:image/png;base64,${qr.qr_base64}` }} style={styles.qr} /><Text style={styles.muted}>Attendees scan this code to check in.</Text></View>}
        <Text style={styles.sectionTitle}>Attendees</Text>
        {attendees.map((attendee) => (
          <View key={attendee.id} style={styles.attendeeRow}>
            <View><Text style={styles.cardTitle}>{attendee.full_name}</Text><Text style={styles.muted}>{attendee.email || "No email"}</Text></View>
            <View style={styles.attendeeActions}><Text style={[styles.status, attendee.check_in_status === "checked_in" && styles.checkedIn]}>{attendee.check_in_status.replace("_", " ")}</Text><Pressable onPress={() => showAttendeeQR(attendee)}><Text style={styles.qrLink}>QR</Text></Pressable></View>
          </View>
        ))}
        {attendeeQR && <View style={styles.qrCard}><Text style={styles.cardTitle}>{attendeeQR.attendee.full_name}'s personal QR</Text><Image source={{ uri: `data:image/png;base64,${attendeeQR.qr.qr_base64}` }} style={styles.qr} /><Text style={styles.muted}>Show this code to the coordinator for check-in.</Text></View>}
        <Button title="Refresh" onPress={load} secondary />
      </ScrollView>
    </Screen>
  );
}

function AddAttendeeScreen({ route, navigation }: any) {
  const { eventId } = route.params as { eventId: number };
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [studentId, setStudentId] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!name) {
      Alert.alert("Missing name", "Enter the attendee's name first.");
      return;
    }
    setBusy(true);
    try {
      await addAttendee(eventId, { full_name: name, email: email || undefined, student_id: studentId || undefined });
      navigation.goBack();
    } catch (error) {
      Alert.alert("Could not add attendee", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  return <Screen><ScrollView contentContainerStyle={styles.formContainer}><Text style={styles.screenTitle}>Add attendee</Text><Field label="Full name" value={name} onChangeText={setName} placeholder="Attendee name" /><Field label="Email" value={email} onChangeText={setEmail} placeholder="Optional email" /><Field label="Student ID" value={studentId} onChangeText={setStudentId} placeholder="Optional student ID" />{busy ? <Loading /> : <Button title="Add attendee" onPress={submit} />}</ScrollView></Screen>;
}

function parseCheckInCode(data: string): { screen: "CheckIn" | "PersonalCheckIn" | "AccountCheckIn"; token: string } | null {
  const normalized = data.trim().replace(/\/+$/, "");
  const match = normalized.match(/^qrevent:\/\/(checkin|attendee|account)\/([^/?#]+)$/i);
  if (!match) return null;

  return {
    screen: match[1].toLowerCase() === "attendee" ? "PersonalCheckIn" : match[1].toLowerCase() === "account" ? "AccountCheckIn" : "CheckIn",
    token: decodeURIComponent(match[2]),
  };
}

function QRScannerScreen({ route, navigation }: any) {
  const eventId = (route?.params as { eventId?: number } | undefined)?.eventId;
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [scanMessage, setScanMessage] = useState("Align the QR code inside the frame");

  if (!permission) return <Screen><Loading /></Screen>;
  if (!permission.granted) return <Screen><View style={styles.center}><Text style={styles.screenTitle}>Camera access needed</Text><Text style={styles.subtitle}>Allow camera access to scan an event QR code.</Text><Button title="Allow camera" onPress={requestPermission} /></View></Screen>;

  function handleBarcodeScanned({ data }: { data: string }) {
    const result = parseCheckInCode(data);
    if (!result) {
      setScanMessage("That QR code is not a QR Event code. Try an event or attendee QR.");
      return;
    }

    setScanned(true);
    setScanMessage("QR code found. Loading check-in...");
    if (result.screen === "AccountCheckIn") {
      if (!eventId) {
        setScanned(false);
        setScanMessage("Open the scanner from a specific event to check in a student.");
        return;
      }
      checkInAccount(eventId, result.token)
        .then((attendee) => { Alert.alert("Student checked in", `${attendee.full_name} is on the event list and is now checked in.`); navigation.goBack(); })
        .catch((error) => { setScanned(false); setScanMessage(apiError(error)); });
      return;
    }
    if (result.screen === "PersonalCheckIn") {
      navigation.replace(result.screen, { attendeeQrToken: result.token });
    } else {
      navigation.replace(result.screen, { qrToken: result.token });
    }
  }

  return <Screen><View style={styles.scanner}><CameraView
    barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
    onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
    onMountError={() => setScanMessage("Camera could not start. Check camera permission in phone settings.")}
    style={StyleSheet.absoluteFillObject}
  /><View style={styles.scanFrame} /><Text style={styles.scanHint}>{scanMessage}</Text></View></Screen>;
}

function PersonalCheckInScreen({ route, navigation }: any) {
  const { attendeeQrToken } = route.params as { attendeeQrToken: string };
  const [checkIn, setCheckIn] = useState<PersonalCheckIn | null>(null);
  const [busy, setBusy] = useState(true);

  useEffect(() => { getPersonalCheckIn(attendeeQrToken).then(setCheckIn).catch((error) => Alert.alert("Invalid attendee QR", apiError(error))).finally(() => setBusy(false)); }, [attendeeQrToken]);

  async function confirmCheckIn() {
    try {
      const attendee = await checkInPersonal(attendeeQrToken);
      Alert.alert("Checked in", `${attendee.full_name} is checked in.`);
      navigation.popToTop();
    } catch (error) {
      Alert.alert("Could not check in", apiError(error));
    }
  }

  if (busy) return <Screen><Loading /></Screen>;
  if (!checkIn) return <Screen><View style={styles.center}><Text style={styles.screenTitle}>Attendee QR unavailable</Text></View></Screen>;
  return <Screen><View style={styles.formContainer}><Text style={styles.screenTitle}>Confirm check-in</Text><Text style={styles.subtitle}>{checkIn.event_title}</Text><View style={styles.summaryCard}><Text style={styles.summaryNumber}>{checkIn.attendee.full_name}</Text><Text style={styles.muted}>{checkIn.attendee.check_in_status.replace("_", " ")}</Text></View><Button title="Confirm check-in" onPress={confirmCheckIn} /></View></Screen>;
}

function CheckInScreen({ route, navigation }: any) {
  const { qrToken } = route.params as { qrToken: string };
  const [event, setEvent] = useState<PublicEvent | null>(null);
  const [selected, setSelected] = useState<Attendee | null>(null);
  const [busy, setBusy] = useState(true);

  useEffect(() => { getPublicEvent(qrToken).then(setEvent).catch((error) => Alert.alert("Invalid QR code", apiError(error))).finally(() => setBusy(false)); }, [qrToken]);

  async function submit() {
    if (!selected) return;
    try {
      const attendee = await checkIn(qrToken, selected.id);
      try {
        const permission = await Notifications.requestPermissionsAsync();
        if (permission.granted) {
          const token = await Notifications.getDevicePushTokenAsync();
          await registerDevice(attendee.id, token.data, Platform.OS === "ios" ? "ios" : "android");
        }
      } catch {
        // Notification setup is optional; check-in has already succeeded.
      }
      Alert.alert("Checked in", `${attendee.full_name} is checked in.`);
      navigation.popToTop();
    } catch (error) {
      Alert.alert("Could not check in", apiError(error));
    }
  }

  if (busy) return <Screen><Loading /></Screen>;
  if (!event) return <Screen><View style={styles.center}><Text style={styles.screenTitle}>Event unavailable</Text></View></Screen>;

  return <Screen><ScrollView contentContainerStyle={styles.formContainer}><Text style={styles.screenTitle}>{event.title}</Text><Text style={styles.subtitle}>Select your name to check in.</Text>{event.attendees.map((attendee) => <Pressable key={attendee.id} onPress={() => setSelected(attendee)} style={[styles.selectRow, selected?.id === attendee.id && styles.selectedRow]}><Text style={styles.cardTitle}>{attendee.full_name}</Text><Text style={styles.muted}>{attendee.check_in_status.replace("_", " ")}</Text></Pressable>)}<Button title="Confirm check-in" onPress={submit} /></ScrollView></Screen>;
}

export default function App() {
  const [initialRoute, setInitialRoute] = useState<"Login" | "Events" | "AttendeeHome" | null>(null);

  useEffect(() => {
    hasAccessToken().then(async (token) => {
      if (!token) return setInitialRoute("Login");
      try {
        const sessionType = await getSessionType();
        if (sessionType === "attendee") { await getAttendeeMe(); setInitialRoute("AttendeeHome"); }
        else { const profile = await getMe(); setInitialRoute(profile.role === "admin" ? "AdminHome" : "Events"); }
      } catch { await logout(); setInitialRoute("Login"); }
    });
  }, []);

  if (!initialRoute) return <Screen><Loading /></Screen>;
  return <NavigationContainer><Stack.Navigator initialRouteName={initialRoute}><Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} /><Stack.Screen name="Events" component={EventsScreen} options={{ title: "Event Book" }} /><Stack.Screen name="AdminHome" component={AdminHomeScreen} options={{ title: "Admin Center" }} /><Stack.Screen name="AttendeeHome" component={AttendeeHomeScreen} options={{ title: "Student QR" }} /><Stack.Screen name="CreateEvent" component={CreateEventScreen} options={{ title: "Create event" }} /><Stack.Screen name="EventDetail" component={EventDetailScreen} options={{ title: "Event detail" }} /><Stack.Screen name="AddAttendee" component={AddAttendeeScreen} options={{ title: "Add attendee" }} /><Stack.Screen name="QRScanner" component={QRScannerScreen} options={{ title: "Scan QR" }} /><Stack.Screen name="CheckIn" component={CheckInScreen} options={{ title: "Check in" }} /><Stack.Screen name="PersonalCheckIn" component={PersonalCheckInScreen} options={{ title: "Personal check-in" }} /></Stack.Navigator></NavigationContainer>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  authContainer: { flexGrow: 1, justifyContent: "center", padding: 24 },
  formContainer: { padding: 20, gap: 14 },
  brand: { color: colors.primary, fontSize: 18, fontWeight: "800", marginBottom: 24 },
  heroTitle: { color: colors.ink, fontSize: 32, fontWeight: "800", marginBottom: 8 },
  screenTitle: { color: colors.ink, fontSize: 26, fontWeight: "800" },
  sectionTitle: { color: colors.ink, fontSize: 20, fontWeight: "800", marginTop: 18 },
  subtitle: { color: colors.muted, fontSize: 15, lineHeight: 22, marginBottom: 16 },
  label: { color: colors.ink, fontSize: 13, fontWeight: "700", marginBottom: 6 },
  fieldGroup: { marginBottom: 4 },
  input: { backgroundColor: colors.card, borderColor: colors.border, borderWidth: 1, borderRadius: 12, color: colors.ink, padding: 14, fontSize: 16 },
  button: { alignItems: "center", backgroundColor: colors.primary, borderRadius: 12, marginVertical: 4, padding: 15, flex: 1 },
  buttonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "800" },
  accountToggle: { backgroundColor: colors.card, borderColor: colors.border, borderRadius: 12, borderWidth: 1, flexDirection: "row", marginBottom: 20, padding: 4 },
  toggleOption: { borderRadius: 9, flex: 1, padding: 10 },
  toggleOptionActive: { backgroundColor: "#E7ECFF" },
  toggleText: { color: colors.ink, fontSize: 14, fontWeight: "800", textAlign: "center" },
  secondaryButton: { backgroundColor: colors.card, borderColor: colors.border, borderWidth: 1 },
  secondaryButtonText: { color: colors.primary },
  link: { color: colors.primary, fontSize: 14, fontWeight: "700", paddingVertical: 12, textAlign: "center" },
  divider: { borderTopColor: colors.border, borderTopWidth: 1, marginVertical: 10 },
  loading: { margin: 24 },
  headerRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", padding: 20 },
  actionRow: { flexDirection: "row", gap: 10, paddingHorizontal: 20 },
  listContent: { gap: 12, padding: 20 },
  card: { backgroundColor: colors.card, borderColor: colors.border, borderRadius: 16, borderWidth: 1, padding: 16 },
  cardHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  cardTitle: { color: colors.ink, fontSize: 16, fontWeight: "800" },
  badge: { backgroundColor: "#E7ECFF", borderRadius: 10, color: colors.primary, fontSize: 12, fontWeight: "700", overflow: "hidden", paddingHorizontal: 8, paddingVertical: 4 },
  muted: { color: colors.muted, fontSize: 13, marginTop: 3 },
  stats: { color: colors.success, fontSize: 13, fontWeight: "700", marginTop: 12 },
  empty: { color: colors.muted, padding: 24, textAlign: "center" },
  summaryCard: { alignItems: "center", backgroundColor: colors.card, borderRadius: 16, padding: 20 },
  summaryNumber: { color: colors.primary, fontSize: 34, fontWeight: "800" },
  adminSummary: { backgroundColor: colors.card, borderColor: colors.border, borderRadius: 16, borderWidth: 1, flexDirection: "row", justifyContent: "space-around", padding: 18 },
  adminMetric: { alignItems: "center", flex: 1 },
  qrCard: { alignItems: "center", backgroundColor: colors.card, borderRadius: 16, padding: 20 },
  qr: { height: 220, width: 220 },
  attendeeRow: { alignItems: "center", backgroundColor: colors.card, borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: 14 },
  attendeeActions: { alignItems: "center", flexDirection: "row", gap: 12 },
  qrLink: { color: colors.primary, fontSize: 13, fontWeight: "800" },
  status: { color: colors.muted, fontSize: 12, textTransform: "capitalize" },
  checkedIn: { color: colors.success, fontWeight: "800" },
  inactive: { color: colors.danger, fontWeight: "800" },
  adminRow: { alignItems: "center", backgroundColor: colors.card, borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: 14 },
  center: { alignItems: "center", flex: 1, justifyContent: "center", padding: 24 },
  scanner: { backgroundColor: "#101828", flex: 1, justifyContent: "flex-end", overflow: "hidden" },
  scanFrame: { alignSelf: "center", borderColor: "#FFFFFF", borderRadius: 20, borderWidth: 3, height: 240, marginBottom: 180, width: 240 },
  scanHint: { color: "#FFFFFF", fontSize: 15, fontWeight: "700", marginBottom: 70, textAlign: "center" },
  selectRow: { backgroundColor: colors.card, borderColor: colors.border, borderRadius: 12, borderWidth: 1, padding: 16 },
  selectedRow: { backgroundColor: "#E7ECFF", borderColor: colors.primary },
});
