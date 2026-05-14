import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Users, Calendar, BookOpen, Bell, CheckCircle, XCircle,
  Clock, Mail, Eye, Plus, Search, Filter, ChevronDown,
  AlertCircle, User, FileText, Send
} from "lucide-react";

const TABS = [
  { icon: Users, label: "Bewerbungen", count: 4 },
  { icon: Calendar, label: "Dienstplan", count: 0 },
  { icon: BookOpen, label: "Schulungen", count: 0 },
  { icon: Bell, label: "Informationen", count: 0 },
];

const BEWERBUNGEN = [
  { id: 1, name: "Thomas Gruber",   role: "DGKP",  date: "05.05.2026", status: "ausstehend",  docs: 3, email: "t.gruber@email.at", region: "Wien-Nord" },
  { id: 2, name: "Anna Schneider",  role: "PFA",   date: "03.05.2026", status: "gespräch",   docs: 5, email: "anna.s@mail.com",    region: "Wien-Süd" },
  { id: 3, name: "Josef Baumgartner",role:"PA",    date: "01.05.2026", status: "freigegeben", docs: 5, email: "j.baum@aon.at",      region: "Wien-West" },
  { id: 4, name: "Mira Holzer",     role: "DGKP",  date: "28.04.2026", status: "abgelehnt",  docs: 2, email: "mira.h@email.at",    region: "Wien-Ost" },
];

const DIENSTE = [
  { id: 1, date: "08.05.", art: "Frühdienst",  fahrzeug: "W-NRY-01", name: "Maria Kovač",     status: "bestätigt" },
  { id: 2, date: "08.05.", art: "Spätdienst",  fahrzeug: "W-NRY-02", name: "Thomas Gruber",   status: "offen" },
  { id: 3, date: "09.05.", art: "Frühdienst",  fahrzeug: "W-NRY-01", name: "Anna Schneider",  status: "bestätigt" },
  { id: 4, date: "09.05.", art: "Nachtdienst", fahrzeug: "W-NRY-03", name: "— offen —",       status: "unbesetzt" },
  { id: 5, date: "10.05.", art: "Frühdienst",  fahrzeug: "W-NRY-02", name: "Josef Baumgartner",status:"bestätigt" },
];

const STATUS_STYLES: Record<string, string> = {
  ausstehend:  "border-amber-300 text-amber-600 bg-amber-50",
  gespräch:    "border-blue-300 text-blue-600 bg-blue-50",
  freigegeben: "border-green-300 text-green-600 bg-green-50",
  abgelehnt:   "border-red-300 text-red-500 bg-red-50",
  bestätigt:   "border-green-300 text-green-600 bg-green-50",
  offen:       "border-amber-300 text-amber-600 bg-amber-50",
  unbesetzt:   "border-red-300 text-red-500 bg-red-50",
};

export function AdminVerwaltung() {
  const [activeTab, setActiveTab] = useState(0);
  const [selected, setSelected] = useState<number | null>(1);

  const selectedBew = BEWERBUNGEN.find(b => b.id === selected);

  return (
    <div className="min-h-screen bg-slate-100 flex font-sans text-sm">
      {/* Sidebar */}
      <aside className="w-56 bg-[#1a2744] text-white flex flex-col">
        <div className="px-5 py-6 border-b border-white/10">
          <div className="text-xl font-bold tracking-tight">Nursy</div>
          <div className="text-xs text-blue-300 mt-0.5">Admin · Pflege-Portal</div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {TABS.map((tab, i) => (
            <button
              key={i}
              onClick={() => setActiveTab(i)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                activeTab === i ? "bg-blue-600 text-white" : "text-blue-200 hover:bg-white/10"
              }`}
            >
              <tab.icon className="w-4 h-4 shrink-0" />
              <span className="text-xs font-medium flex-1">{tab.label}</span>
              {tab.count > 0 && (
                <span className="bg-red-500 text-white text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center">{tab.count}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center text-xs font-bold">A</div>
            <div className="text-xs text-blue-200">Admin</div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-slate-800">
              {activeTab === 0 ? "Bewerbungen verwalten" : activeTab === 1 ? "Dienstplan" : activeTab === 2 ? "Schulungen & Events" : "Informationen"}
            </h1>
            <p className="text-xs text-slate-500">
              {activeTab === 0 ? "4 offene Bewerbungen" : "Mai 2026"}
            </p>
          </div>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs gap-1">
            <Plus className="w-3 h-3" />
            {activeTab === 0 ? "Bewerbung prüfen" : activeTab === 1 ? "Dienst hinzufügen" : activeTab === 2 ? "Schulung anlegen" : "Nachricht erstellen"}
          </Button>
        </div>

        {/* Bewerbungen Tab */}
        {activeTab === 0 && (
          <div className="flex flex-1 overflow-hidden">
            {/* List */}
            <div className="w-80 border-r border-slate-200 bg-white overflow-auto">
              <div className="p-3 border-b">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-slate-400" />
                  <Input className="pl-8 h-7 text-xs" placeholder="Suchen..." />
                </div>
              </div>
              <div className="divide-y divide-slate-100">
                {BEWERBUNGEN.map(b => (
                  <button
                    key={b.id}
                    onClick={() => setSelected(b.id)}
                    className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${selected === b.id ? "bg-blue-50 border-l-2 border-blue-500" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-slate-800">{b.name}</span>
                      <Badge variant="outline" className={`text-[9px] py-0 h-4 ${STATUS_STYLES[b.status]}`}>
                        {b.status}
                      </Badge>
                    </div>
                    <div className="text-[10px] text-slate-500">{b.role} · {b.region}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{b.date} · {b.docs}/5 Dokumente</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Detail */}
            {selectedBew && (
              <div className="flex-1 p-5 overflow-auto">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-base">
                      {selectedBew.name.split(" ").map(n => n[0]).join("")}
                    </div>
                    <div>
                      <div className="font-semibold text-slate-800">{selectedBew.name}</div>
                      <div className="text-xs text-slate-500">{selectedBew.role} · {selectedBew.region}</div>
                      <div className="flex items-center gap-1 text-[10px] text-slate-400 mt-0.5">
                        <Mail className="w-3 h-3" />{selectedBew.email}
                      </div>
                    </div>
                  </div>
                  <Badge variant="outline" className={`text-xs ${STATUS_STYLES[selectedBew.status]}`}>
                    {selectedBew.status}
                  </Badge>
                </div>

                {/* Docs */}
                <Card className="mb-4">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5" /> Eingereichte Dokumente ({selectedBew.docs}/5)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1.5">
                    {[
                      { name: "Diplomurkunde", ok: true },
                      { name: "Lichtbildausweis", ok: true },
                      { name: "Strafregisterbescheinigung", ok: true },
                      { name: "Impfnachweis", ok: selectedBew.docs >= 4 },
                      { name: "Referenzschreiben", ok: selectedBew.docs >= 5 },
                    ].map((doc, i) => (
                      <div key={i} className={`flex items-center justify-between px-3 py-1.5 rounded border ${doc.ok ? "border-green-100 bg-green-50" : "border-slate-100 bg-slate-50"}`}>
                        <div className="flex items-center gap-2">
                          {doc.ok ? <CheckCircle className="w-3.5 h-3.5 text-green-500" /> : <AlertCircle className="w-3.5 h-3.5 text-slate-300" />}
                          <span className="text-xs text-slate-700">{doc.name}</span>
                        </div>
                        {doc.ok && <button className="text-[10px] text-blue-500 hover:underline flex items-center gap-0.5"><Eye className="w-3 h-3" /> Ansehen</button>}
                      </div>
                    ))}
                  </CardContent>
                </Card>

                {/* Bewerbungslink */}
                <Card className="mb-4 border-blue-200 bg-blue-50">
                  <CardContent className="p-4 flex items-start gap-3">
                    <Send className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-blue-800 mb-1">Bewerbungslink per E-Mail senden</div>
                      <p className="text-[11px] text-blue-600 leading-snug mb-3">
                        Schickt automatisch einen personalisierten Bewerbungslink an <strong>{selectedBew.email}</strong>. 
                        Das Online-Formular enthält alle relevanten Felder inkl. Terminvereinbarung für das Gespräch.
                      </p>
                      <div className="flex gap-2">
                        <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs h-7 gap-1">
                          <Send className="w-3 h-3" /> Bewerbungslink senden
                        </Button>
                        <Button size="sm" variant="outline" className="text-xs h-7 border-blue-300 text-blue-600">
                          Link kopieren
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white text-xs gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> Freigeben
                  </Button>
                  <Button size="sm" variant="outline" className="text-xs border-amber-300 text-amber-600 gap-1">
                    <Clock className="w-3.5 h-3.5" /> Gespräch ansetzen
                  </Button>
                  <Button size="sm" variant="outline" className="text-xs border-red-300 text-red-500 gap-1">
                    <XCircle className="w-3.5 h-3.5" /> Ablehnen
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Dienstplan Tab */}
        {activeTab === 1 && (
          <div className="p-5">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-slate-700">Dienste – Mai 2026</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b text-slate-500 text-[10px]">
                      <th className="pb-2 text-left font-medium">Datum</th>
                      <th className="pb-2 text-left font-medium">Art</th>
                      <th className="pb-2 text-left font-medium">Fahrzeug</th>
                      <th className="pb-2 text-left font-medium">Pflegeperson</th>
                      <th className="pb-2 text-left font-medium">Status</th>
                      <th className="pb-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {DIENSTE.map(d => (
                      <tr key={d.id} className="hover:bg-slate-50">
                        <td className="py-2 font-medium text-slate-700">{d.date}</td>
                        <td className="py-2 text-slate-600">{d.art}</td>
                        <td className="py-2 text-slate-600">{d.fahrzeug}</td>
                        <td className="py-2 text-slate-700">{d.name}</td>
                        <td className="py-2">
                          <Badge variant="outline" className={`text-[9px] py-0 h-4 ${STATUS_STYLES[d.status]}`}>{d.status}</Badge>
                        </td>
                        <td className="py-2 text-right">
                          <button className="text-blue-500 hover:underline text-[10px]">Bearbeiten</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Schulungen Tab */}
        {activeTab === 2 && (
          <div className="p-5 text-center text-slate-400 text-xs mt-20">
            <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-30" />
            Schulungen & Events hier verwalten
          </div>
        )}

        {/* Info Tab */}
        {activeTab === 3 && (
          <div className="p-5 text-center text-slate-400 text-xs mt-20">
            <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
            Informationen & Ankündigungen hier erstellen
          </div>
        )}
      </main>
    </div>
  );
}
