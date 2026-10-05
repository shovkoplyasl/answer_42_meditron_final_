import React from 'react';
import type{ Patient } from '../data/patients';
import { FileText, CheckCircle, AlertTriangle, User } from 'lucide-react';

interface Props {
  patient: Patient | null;
  onClose: () => void;
  onApprove: (id: string) => void;
}

export const PatientModal: React.FC<Props> = ({ patient, onClose, onApprove }) => {
  if (!patient) return null;

  // Функция для автоподсветки ключевых слов ИИ в тексте протокола
  const renderHighlightedProtocol = (text: string, words: string[]) => {
    if (!words.length) return text;
    const regex = new RegExp(`(${words.join('|')})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, i) =>
      words.some((w) => w.toLowerCase() === part.toLowerCase()) ? (
        <mark key={i} className="bg-yellow-200 text-yellow-900 font-semibold px-1 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-slate-50">
          <div>
            <h2 className="text-xl font-bold text-slate-800">{patient.fullName}</h2>
            <p className="text-sm text-slate-500">
              {patient.gender}, {patient.birthDate} | Лечащий врач: {patient.attendingDoctor}
            </p>
          </div>
          <button
            onClick={() => alert(`Загрузка ЭМК пациента ${patient.fullName}...`)}
            className="flex items-center gap-2 text-sm bg-blue-50 text-blue-600 hover:bg-blue-100 px-3 py-1.5 rounded-lg font-medium transition"
          >
            <FileText className="w-4 h-4" /> Вывод медкарты (ЭМК)
          </button>
        </div>

        {/* Content */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 overflow-y-auto">
          
          {/* Левая колонка: Протокол */}
          <div className="flex flex-col gap-3">
            <h3 className="font-semibold text-slate-700 flex items-center gap-2">
              <User className="w-4 h-4 text-blue-600" /> Протокол исследования (с подсветкой ИИ)
            </h3>
            <div className="p-4 bg-slate-50 border rounded-lg text-sm leading-relaxed whitespace-pre-line text-slate-800 font-mono">
              {renderHighlightedProtocol(patient.protocolText, patient.highlightedWords)}
            </div>
          </div>

          {/* Правая колонка: Анализ ИИ */}
          <div className="flex flex-col gap-4">
            <div className="p-4 rounded-lg border bg-slate-50">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-slate-600">Уверенность модели (CS)</span>
                <span className={`text-sm font-bold ${patient.confidenceScore < 70 ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {patient.confidenceScore}%
                </span>
              </div>
              <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                <div
                  className={`h-2.5 rounded-full ${patient.confidenceScore < 70 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                  style={{ width: `${patient.confidenceScore}%` }}
                ></div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-sm flex gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold mb-1">Комментарий ИИ:</p>
                <p className="leading-snug">{patient.aiComment}</p>
              </div>
            </div>

            <div className="p-4 rounded-lg border bg-slate-50">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Первостепенный маршрут
              </span>
              <p className="text-base font-bold text-slate-800">{patient.suggestedDoctor}</p>
              <p className="text-xs text-slate-500 mt-1">Пуш-уведомление сформировано автоматически</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t bg-slate-50">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded-lg text-slate-600 hover:bg-slate-100 font-medium text-sm transition"
          >
            Свернуть
          </button>
          <button
            onClick={() => onApprove(patient.id)}
            className="flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-sm shadow transition"
          >
            <CheckCircle className="w-4 h-4" /> Утвердить маршрут
          </button>
        </div>

      </div>
    </div>
  );
};