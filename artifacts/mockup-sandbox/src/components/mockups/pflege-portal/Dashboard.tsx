import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Calendar, Bell, BookOpen, LogOut, ChevronLeft, ChevronRight,
  Clock, MapPin, User, CheckCircle, AlertCircle, Info, Plus
} from "lucide-react";

const NAV = [
  { icon: Calendar, label: "Meine Dienste" },
  { icon: BookOpen, label: "Schulungen & Events" },
  { icon: Bell, label: "Informationen" },
  { icon: User, label: "Mein Profil" },
];

const MONTHS = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"];
const DAYS = ["Mo","Di","Mi","Do","Fr","Sa","So"];

const SHIFTS: Record<number, { type: string; color: string }> = {
  2:  { type: "Frühdienst",  color: "bg-blue-500"  },
  5:  { type: "Spätdienst",  color: "bg-purple-500" },
  8:  { type: "Frühdienst",  color: "bg-blue-500"  },
  12: { type: "Nachtdienst", color: "bg-slate-700" },
  15: { type: "Frühdienst",  color: "bg-blue-500"  },
  19: { type: "Spätdienst",  color: "bg-purple-500" },
  22: { type: "Frühdienst",  color: "bg-blue-500"  },
  26: { type: "Nachtdienst", color: "bg-slate-700" },
};

const ANNOUNCEMENTS = [
  { id: 1, type: "info",    title: "Neue Dienstplanrichtlinie ab Juni", date: "05.05.2026", text: "Ab Juni gilt die neue Richtlinie für Überstunden. Bitte Anhang beachten." },
  { id: 2, type: "warning", title: "Pflichtschulung Brandschutz", date: "02.05.2026", text: "Alle Mitarbeiter müssen bis 31.05. die jährliche Brandschutzschulung absolvieren." },
  { id: 3, type: "success", title: "Gehaltserhöhung ab 1. Juni", date: "01.05.2026", text: "Wir freuen uns, eine kollektivvertragliche Erhöhung von 4,2% bekannt zu geben." },
];

const EVENTS = [
  { id: 1, date: "12.05.2026", time: "09:00–12:00", title: "EKG-Grundkurs", type: "Schulung",  slots: 8,  taken: 5 },
  { id: 2, date: "20.05.2026", time: "14:00–17:00", title: "Wundmanagement Update", type: "Schulung", slots: 12, taken: 7 },
  { id: 3, date: "28.05.2026", time: "18:00–20:00", title: "Teamabend Frühjahr", type: "Event",    slots: 40, taken: 22 },
];

export function Dashboard() {
  const [activeNav, setActiveNav] = useState(0);
  const today = 6;
  const year = 2026;
  const month = 4; // May (0-indexed)

  const firstDay = new Date(year, month, 1).getDay();
  const offset = firstDay === 0 ? 6 : firstDay - 1;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (number | null)[] = [
    ...Array(offset).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const nextShifts = Object.entries(SHIFTS)
    .filter(([d]) => parseInt(d) >= today)
    .slice(0, 3)
    .map(([d, s]) => ({ day: parseInt(d), ...s }));

  return (
    <div className="min-h-screen bg-slate-100 flex font-sans text-sm">
      {/* Sidebar */}
      <aside className="w-56 bg-[#1a2744] text-white flex flex-col">
        <div className="px-5 py-6 border-b border-white/10">
          <div className="text-xl font-bold tracking-tight">Nursy</div>
          <div className="text-xs text-blue-300 mt-0.5">Pflege-Portal</div>
        </div>
        <div className="px-3 py-4 border-b border-white/10">
          <div className="flex items-center gap-2 px-2">
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center font-bold text-xs">MK</div>
            <div>
              <div className="text-xs font-semibold leading-tight">Maria Kovač</div>
              <div className="text-[10px] text-blue-300">Pflegerin · Wien</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map((item, i) => (
            <button
              key={i}
              onClick={() => setActiveNav(i)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                activeNav === i ? "bg-blue-600 text-white" : "text-blue-200 hover:bg-white/10"
              }`}
            >
              <item.icon className="w-4 h-4 shrink-0" />
              <span className="text-xs font-medium">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="p-3">
          <button className="w-full flex items-center gap-2 px-3 py-2 text-blue-300 hover:text-white text-xs">
            <LogOut className="w-4 h-4" /> Abmelden
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-slate-800">Meine Dienste</h1>
            <p className="text-xs text-slate-500">Mai 2026 · Dienstplan & Eintragungen</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="relative p-2 rounded-lg hover:bg-slate-100">
              <Bell className="w-4 h-4 text-slate-600" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            </button>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs gap-1">
              <Plus className="w-3 h-3" /> Dienst eintragen
            </Button>
          </div>
        </div>

        <div className="p-5 grid grid-cols-3 gap-4">
          {/* Calendar – 2 cols wide */}
          <div className="col-span-2 space-y-4">
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-blue-600" /> Mai 2026
                </CardTitle>
                <div className="flex gap-1">
                  <button className="p-1 rounded hover:bg-slate-100"><ChevronLeft className="w-4 h-4 text-slate-500" /></button>
                  <button className="p-1 rounded hover:bg-slate-100"><ChevronRight className="w-4 h-4 text-slate-500" /></button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-7 gap-0.5 mb-1">
                  {DAYS.map(d => (
                    <div key={d} className="text-center text-[10px] font-semibold text-slate-400 py-1">{d}</div>
                  ))}
                </div>
                <div className="grid grid-cols-7 gap-0.5">
                  {cells.map((day, i) => {
                    if (!day) return <div key={`e${i}`} />;
                    const shift = SHIFTS[day];
                    const isToday = day === today;
                    return (
                      <div
                        key={day}
                        className={`relative rounded-lg p-1 min-h-[44px] cursor-pointer hover:bg-slate-50 border ${
                          isToday ? "border-blue-500 bg-blue-50" : "border-transparent"
                        }`}
                      >
                        <div className={`text-xs font-semibold mb-1 ${isToday ? "text-blue-600" : "text-slate-700"}`}>{day}</div>
                        {shift && (
                          <div className={`${shift.color} text-white text-[9px] px-1 py-0.5 rounded truncate`}>
                            {shift.type.split("dienst")[0]}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-3 mt-3 border-t pt-3">
                  {[
                    { color: "bg-blue-500",  label: "Frühdienst" },
                    { color: "bg-purple-500", label: "Spätdienst" },
                    { color: "bg-slate-700",  label: "Nachtdienst" },
                  ].map(l => (
                    <div key={l.label} className="flex items-center gap-1.5 text-[10px] text-slate-500">
                      <span className={`w-2.5 h-2.5 rounded-sm ${l.color}`} />{l.label}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Upcoming Events */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-purple-600" /> Nächste Schulungen & Events
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {EVENTS.map(ev => (
                  <div key={ev.id} className="flex items-center gap-3 p-3 rounded-lg border border-slate-100 hover:border-slate-200">
                    <div className="text-center bg-slate-100 rounded-lg px-2 py-1 min-w-[48px]">
                      <div className="text-[9px] text-slate-500">{ev.date.split(".")[1]}/{ev.date.split(".")[2].slice(2)}</div>
                      <div className="text-sm font-bold text-slate-700">{ev.date.split(".")[0]}</div>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-slate-800 text-xs">{ev.title}</div>
                      <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-500">
                        <Clock className="w-3 h-3" />{ev.time}
                        <span className="text-slate-300">·</span>
                        <span>{ev.taken}/{ev.slots} Plätze</span>
                      </div>
                    </div>
                    <Badge variant="outline" className={`text-[9px] ${ev.type === "Schulung" ? "border-purple-300 text-purple-600" : "border-green-300 text-green-600"}`}>
                      {ev.type}
                    </Badge>
                    <Button size="sm" variant="outline" className="text-[10px] h-6 px-2">Anmelden</Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Right column */}
          <div className="space-y-4">
            {/* Next shift highlight */}
            {nextShifts[0] && (
              <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-white">
                <CardContent className="pt-4">
                  <div className="text-[10px] text-blue-500 font-semibold uppercase tracking-wider mb-1">Nächster Dienst</div>
                  <div className="text-2xl font-bold text-slate-800">{nextShifts[0].day}. Mai</div>
                  <div className={`inline-block mt-1 ${nextShifts[0].color} text-white text-xs px-2 py-0.5 rounded-full`}>
                    {nextShifts[0].type}
                  </div>
                  <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
                    <MapPin className="w-3 h-3" /> Wien-Floridsdorf
                  </div>
                  <div className="flex items-center gap-1 text-xs text-slate-500">
                    <Clock className="w-3 h-3" /> 06:00 – 14:00 Uhr
                  </div>
                </CardContent>
              </Card>
            )}

            {/* More shifts */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-slate-600">Weitere Dienste im Mai</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {nextShifts.slice(1).map(s => (
                  <div key={s.day} className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${s.color}`} />
                    <span className="text-xs text-slate-700 font-medium">{s.day}. Mai</span>
                    <span className="text-[10px] text-slate-500 ml-auto">{s.type}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Announcements */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                  <Bell className="w-3.5 h-3.5" /> Informationen
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {ANNOUNCEMENTS.map(a => {
                  const Icon = a.type === "warning" ? AlertCircle : a.type === "success" ? CheckCircle : Info;
                  const color = a.type === "warning" ? "text-amber-500" : a.type === "success" ? "text-green-500" : "text-blue-500";
                  return (
                    <div key={a.id} className="p-2 rounded-lg border border-slate-100">
                      <div className="flex items-start gap-1.5">
                        <Icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${color}`} />
                        <div>
                          <div className="text-[11px] font-semibold text-slate-700 leading-tight">{a.title}</div>
                          <div className="text-[10px] text-slate-400 mt-0.5">{a.date}</div>
                          <div className="text-[10px] text-slate-500 mt-1 leading-snug">{a.text}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
