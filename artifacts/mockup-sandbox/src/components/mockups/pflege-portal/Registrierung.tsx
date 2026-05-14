import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle, Upload, User, Mail, Phone, MapPin,
  FileText, ChevronRight, Lock, AlertCircle, Info
} from "lucide-react";

const STEPS = ["Persönliche Daten", "Qualifikationen", "Dokumente hochladen", "Abschluss"];

export function Registrierung() {
  const [step, setStep] = useState(2); // 0-based, show step 2 = Dokumente
  const [uploaded, setUploaded] = useState<string[]>(["Diplomurkunde_Kovac.pdf"]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1a2744] to-[#243560] flex flex-col items-center justify-start py-10 px-4 font-sans">
      {/* Logo */}
      <div className="text-white text-center mb-8">
        <div className="text-3xl font-bold tracking-tight">Nursy</div>
        <div className="text-blue-300 text-sm mt-0.5">Pflege-Portal · Bewerbung & Registrierung</div>
      </div>

      {/* Stepper */}
      <div className="w-full max-w-2xl mb-6">
        <div className="flex items-center justify-between relative">
          <div className="absolute top-4 left-0 right-0 h-0.5 bg-white/20" />
          <div className="absolute top-4 left-0 h-0.5 bg-blue-400 transition-all" style={{ width: `${(step / (STEPS.length - 1)) * 100}%` }} />
          {STEPS.map((s, i) => (
            <div key={i} className="relative flex flex-col items-center z-10">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${
                i < step ? "bg-blue-500 border-blue-500 text-white"
                : i === step ? "bg-white border-white text-blue-700 font-bold"
                : "bg-[#1a2744] border-white/30 text-white/50"
              }`}>
                {i < step ? <CheckCircle className="w-4 h-4" /> : <span className="text-xs">{i + 1}</span>}
              </div>
              <span className={`text-[10px] mt-1 font-medium text-center max-w-[64px] leading-tight ${
                i === step ? "text-white" : "text-white/50"
              }`}>{s}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Card */}
      <Card className="w-full max-w-2xl shadow-2xl border-0">
        <CardContent className="p-6">
          {step === 0 && (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-slate-800 mb-4">Persönliche Daten</h2>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="text-xs">Vorname *</Label><Input className="mt-1 h-8 text-sm" placeholder="Maria" /></div>
                <div><Label className="text-xs">Nachname *</Label><Input className="mt-1 h-8 text-sm" placeholder="Kovač" /></div>
              </div>
              <div><Label className="text-xs">E-Mail Adresse *</Label><Input className="mt-1 h-8 text-sm" type="email" placeholder="maria.kovac@email.at" /></div>
              <div><Label className="text-xs">Telefonnummer *</Label><Input className="mt-1 h-8 text-sm" placeholder="+43 ..." /></div>
              <div><Label className="text-xs">Wohnort *</Label><Input className="mt-1 h-8 text-sm" placeholder="Wien" /></div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-slate-800 mb-4">Qualifikationen & Ausbildung</h2>
              <div>
                <Label className="text-xs">Pflegeausbildung *</Label>
                <select className="mt-1 w-full border rounded-md h-8 text-sm px-2 bg-white">
                  <option>Diplomierte Gesundheits- und Krankenpflege (DGKP)</option>
                  <option>Pflegefachassistenz (PFA)</option>
                  <option>Pflegeassistenz (PA)</option>
                  <option>Heimhilfe</option>
                </select>
              </div>
              <div><Label className="text-xs">Berufserfahrung (Jahre)</Label><Input className="mt-1 h-8 text-sm" placeholder="5" /></div>
              <div><Label className="text-xs">Gewünschte Dienstarten</Label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {["Frühdienst","Spätdienst","Nachtdienst","Wochenenddienst"].map(d => (
                    <label key={d} className="flex items-center gap-1.5 text-xs bg-slate-50 border rounded px-2 py-1 cursor-pointer hover:bg-blue-50">
                      <input type="checkbox" className="w-3 h-3" defaultChecked={d !== "Nachtdienst"} /> {d}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-slate-800 mb-1">Dokumente hochladen</h2>
              <p className="text-xs text-slate-500 mb-4">Bitte laden Sie die folgenden Unterlagen hoch. Nach Einreichung wird ein Bewerbungsgespräch vereinbart und Sie erhalten automatisch einen persönlichen Bewerbungslink per E-Mail.</p>

              <div className="space-y-2">
                {[
                  { name: "Diplomurkunde / Ausbildungsnachweis", required: true, done: true },
                  { name: "Lichtbildausweis (Vorder- & Rückseite)", required: true, done: false },
                  { name: "Strafregisterbescheinigung (max. 3 Monate alt)", required: true, done: false },
                  { name: "Impfnachweis (COVID-19, Hepatitis B)", required: false, done: false },
                  { name: "Referenzschreiben (optional)", required: false, done: false },
                ].map((doc, i) => (
                  <div key={i} className={`flex items-center justify-between p-3 rounded-lg border ${doc.done ? "border-green-200 bg-green-50" : "border-slate-200 bg-white"}`}>
                    <div className="flex items-center gap-2">
                      {doc.done
                        ? <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                        : <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                      }
                      <span className="text-xs text-slate-700">{doc.name}</span>
                      {doc.required && <Badge variant="outline" className="text-[9px] border-red-200 text-red-500 py-0 h-4">Pflicht</Badge>}
                    </div>
                    {doc.done
                      ? <span className="text-[10px] text-green-600 font-medium">{uploaded[0]}</span>
                      : <button className="flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-700 border border-blue-200 rounded px-2 py-1">
                          <Upload className="w-3 h-3" /> Hochladen
                        </button>
                    }
                  </div>
                ))}
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex gap-2 mt-2">
                <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                <p className="text-[11px] text-blue-700 leading-snug">
                  Nach dem Einreichen Ihrer Unterlagen wird Ihr Profil von unserem Admiral oder Admin geprüft. 
                  Sie erhalten anschließend eine E-Mail mit einem persönlichen <strong>Bewerbungslink</strong> für ein Online-Formular sowie einem Terminvorschlag für das Bewerbungsgespräch.
                </p>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="text-center py-6 space-y-3">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-8 h-8 text-green-500" />
              </div>
              <h2 className="text-base font-semibold text-slate-800">Bewerbung eingereicht!</h2>
              <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                Ihre Unterlagen wurden erfolgreich übermittelt. Wir prüfen Ihre Bewerbung und melden uns innerhalb von 2–3 Werktagen bei Ihnen per E-Mail.
              </p>
              <div className="bg-slate-50 border rounded-lg p-3 text-left mx-auto max-w-xs">
                <div className="text-[10px] text-slate-500 mb-1">Ihr Bewerbungslink wurde gesendet an:</div>
                <div className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
                  <Mail className="w-3.5 h-3.5 text-blue-500" /> maria.kovac@email.at
                </div>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between mt-6 pt-4 border-t">
            <Button variant="ghost" size="sm" className="text-xs" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
              Zurück
            </Button>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs gap-1"
              onClick={() => setStep(Math.min(STEPS.length - 1, step + 1))}>
              {step === STEPS.length - 2 ? "Absenden" : step === STEPS.length - 1 ? "Zum Portal" : "Weiter"}
              <ChevronRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-blue-300/60 text-[10px] mt-6">Bereits registriert? <span className="text-blue-300 underline cursor-pointer">Hier anmelden</span></p>
    </div>
  );
}
