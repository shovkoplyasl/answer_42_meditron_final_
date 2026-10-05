import { useState } from 'react';
import { request } from '../api';
export default function ProtocolUpload({onClose,onSaved}: {onClose:()=>void;onSaved:()=>Promise<void>}) {
  const [text,setText]=useState(''); const [patient,setPatient]=useState(''); const [file,setFile]=useState<File|null>(null);
  const [busy,setBusy]=useState(false); const [error,setError]=useState('');
  async function submit() {
    setBusy(true);setError('');
    try {
      if (!file && !text.trim()) throw new Error('Введите текст или выберите DOCX');
      if (patient && (!Number.isInteger(Number(patient)) || Number(patient)<1)) throw new Error('Некорректный ID пациента');
      const id=patient ? Number(patient) : (await request<{id:number}>('/api/v1/patients',{})).id;
      if(file) { const data=new FormData();data.append('file',file);await request(`/api/v1/analyze/file?patient_id=${id}`,data); }
      else await request('/api/v1/analyze',{patient_id:id,protocol_text:text,file_name:'Введённый текст'});
      await onSaved();onClose();
    } catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  return <div className="fixed inset-0 z-50 bg-[#404040]/60 flex items-center justify-center p-4"><div className="bg-white rounded-2xl p-6 w-full max-w-2xl space-y-4 shadow-xl">
    <h2 className="font-bold text-xl">Добавить протокол</h2>
    <p className="text-xs text-gray-500">Анализ и сохранение выполняются бэкендом FINAL. Не диагноз и не назначение лечения.</p>
    <input aria-label="ID пациента" placeholder="ID существующего пациента (пусто — создать нового)" className="border rounded-xl p-3 w-full" value={patient} onChange={e=>setPatient(e.target.value)}/>
    <textarea aria-label="Текст протокола" placeholder="Текст протокола" className="border rounded-xl p-3 w-full h-52" value={text} maxLength={150000} disabled={!!file} onChange={e=>setText(e.target.value)}/>
    <label className="block text-sm">Или файл DOCX до 12 МБ<input type="file" accept=".docx" className="block mt-2" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
    {error && <p role="alert" className="text-red-600 text-sm">{error}</p>}
    <div className="flex gap-3 justify-end"><button disabled={busy} onClick={onClose} className="px-4 py-2 rounded-xl border">Отмена</button><button disabled={busy} onClick={submit} className="bg-[#13AB7B] text-white px-4 py-2 rounded-xl disabled:opacity-50">{busy?'Обработка…':'Проанализировать и сохранить'}</button></div>
  </div></div>;
}
