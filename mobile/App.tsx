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
import { NavigationContainer } from "@react-navigation/native";
import { useFocusEffect } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import {
  addAttendee,
  apiError,
  checkIn,
  createEvent,
  checkInPersonal,
  getAttendeeQR,
  getEvent,
  getMe,
  getPersonalCheckIn,
  getPublicEvent,
  getQR,
  hasAccessToken,
  listAttendees,
  listEvents,
  login,
  logout,
  notifyAll,
  register,
  registerDevice,
} from "./src/api";
import { Attendee, Event, PersonalCheckIn, PublicEvent, QRResponse } from "./src/types";

type RootStackParamList = {
  Login: undefined;
  Events: undefined;
  CreateEvent: undefined;
  EventDetail: { eventId: number };
  AddAttendee: { eventId: number };
  QRScanner: undefined;
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
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!email || !password || (mode === "register" && !name)) {
      Alert.alert("Missing details", "Please complete all required fields.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(name, email, password);
      navigation.replace("Events");
    } catch (error) {
      Alert.alert("Unable to continue", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.authContainer} keyboardShouldPersistTaps="handled">
          <Text style={styles.brand}>QR Event</Text>
          <Text style={styles.heroTitle}>{mode === "login" ? "Welcome back" : "Create your account"}</Text>
          <Text style={styles.subtitle}>Manage events, attendees, check-ins, and notifications in one place.</Text>
          {mode === "register" && <Field label="Name" value={name} onChangeText={setName} placeholder="Your full name" />}
          <Field label="Email" value={email} onChangeText={setEmail} placeholder="you@example.com" />
          <Field label="Password" value={password} onChangeText={setPassword} placeholder="At least 6 characters" secureTextEntry />
          {busy ? <Loading /> : <Button title={mode === "login" ? "Log in" : "Register"} onPress={submit} />}
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

function EventsScreen({ navigation }: any) {
  const [events, setEvents] = useState<Event[]>([]);
  const [busy, setBusy] = useState(true);

  async function load() {
    setBusy(true);
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

  async function load() {
    setBusy(true);
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
    load();
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
        <Text style={styles.subtitle}>{event.location || "No location"}</Text>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryNumber}>{event.checked_in_count}/{event.attendee_count}</Text>
          <Text style={styles.muted}>checked in</Text>
        </View>
        <View style={styles.actionRow}>
          <Button title="Show event QR" onPress={showQR} />
          <Button title="Notify all" onPress={sendNotification} secondary />
        </View>
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
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!name) {
      Alert.alert("Missing name", "Enter the attendee's name first.");
      return;
    }
    setBusy(true);
    try {
      await addAttendee(eventId, { full_name: name, email: email || undefined });
      navigation.goBack();
    } catch (error) {
      Alert.alert("Could not add attendee", apiError(error));
    } finally {
      setBusy(false);
    }
  }

  return <Screen><ScrollView contentContainerStyle={styles.formContainer}><Text style={styles.screenTitle}>Add attendee</Text><Field label="Full name" value={name} onChangeText={setName} placeholder="Attendee name" /><Field label="Email" value={email} onChangeText={setEmail} placeholder="Optional email" />{busy ? <Loading /> : <Button title="Add attendee" onPress={submit} />}</ScrollView></Screen>;
}

function QRScannerScreen({ navigation }: any) {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);

  if (!permission) return <Screen><Loading /></Screen>;
  if (!permission.granted) return <Screen><View style={styles.center}><Text style={styles.screenTitle}>Camera access needed</Text><Text style={styles.subtitle}>Allow camera access to scan an event QR code.</Text><Button title="Allow camera" onPress={requestPermission} /></View></Screen>;

  return <Screen><View style={styles.scanner}><CameraView barcodeScannerSettings={{ barcodeTypes: ["qr"] }} onBarcodeScanned={scanned ? undefined : ({ data }) => { setScanned(true); const token = data.split("/").pop(); if (token) navigation.replace(data.includes("/attendee/") ? "PersonalCheckIn" : "CheckIn", data.includes("/attendee/") ? { attendeeQrToken: token } : { qrToken: token }); }} style={StyleSheet.absoluteFillObject} /><View style={styles.scanFrame} /><Text style={styles.scanHint}>Align the QR code inside the frame</Text></View></Screen>;
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
  const [initialRoute, setInitialRoute] = useState<"Login" | "Events" | null>(null);

  useEffect(() => {
    hasAccessToken().then(async (token) => {
      if (!token) return setInitialRoute("Login");
      try { await getMe(); setInitialRoute("Events"); } catch { await logout(); setInitialRoute("Login"); }
    });
  }, []);

  if (!initialRoute) return <Screen><Loading /></Screen>;
  return <NavigationContainer><Stack.Navigator initialRouteName={initialRoute}><Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} /><Stack.Screen name="Events" component={EventsScreen} options={{ title: "Event Book" }} /><Stack.Screen name="CreateEvent" component={CreateEventScreen} options={{ title: "Create event" }} /><Stack.Screen name="EventDetail" component={EventDetailScreen} options={{ title: "Event detail" }} /><Stack.Screen name="AddAttendee" component={AddAttendeeScreen} options={{ title: "Add attendee" }} /><Stack.Screen name="QRScanner" component={QRScannerScreen} options={{ title: "Scan QR" }} /><Stack.Screen name="CheckIn" component={CheckInScreen} options={{ title: "Check in" }} /><Stack.Screen name="PersonalCheckIn" component={PersonalCheckInScreen} options={{ title: "Personal check-in" }} /></Stack.Navigator></NavigationContainer>;
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
  qrCard: { alignItems: "center", backgroundColor: colors.card, borderRadius: 16, padding: 20 },
  qr: { height: 220, width: 220 },
  attendeeRow: { alignItems: "center", backgroundColor: colors.card, borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: 14 },
  attendeeActions: { alignItems: "center", flexDirection: "row", gap: 12 },
  qrLink: { color: colors.primary, fontSize: 13, fontWeight: "800" },
  status: { color: colors.muted, fontSize: 12, textTransform: "capitalize" },
  checkedIn: { color: colors.success, fontWeight: "800" },
  center: { alignItems: "center", flex: 1, justifyContent: "center", padding: 24 },
  scanner: { backgroundColor: "#101828", flex: 1, justifyContent: "flex-end", overflow: "hidden" },
  scanFrame: { alignSelf: "center", borderColor: "#FFFFFF", borderRadius: 20, borderWidth: 3, height: 240, marginBottom: 180, width: 240 },
  scanHint: { color: "#FFFFFF", fontSize: 15, fontWeight: "700", marginBottom: 70, textAlign: "center" },
  selectRow: { backgroundColor: colors.card, borderColor: colors.border, borderRadius: 12, borderWidth: 1, padding: 16 },
  selectedRow: { backgroundColor: "#E7ECFF", borderColor: colors.primary },
});
