import { useEffect, useState } from 'react';
import { request } from '../api';
interface Slot {id:string;date:string;label:string;doctor:string;specialist:string;clinic:string}
interface Props {isOpen:boolean;routeId:number|null;onClose:()=>void;onSaved:()=>Promise<void>}
export function PatientBookingModal({isOpen,routeId,onClose,onSaved}:Props) {
  const [slots,setSlots]=useState<Slot[]>([]);const [selected,setSelected]=useState('');
  const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
  useEffect(()=>{
    if(!isOpen || !routeId)return;
    let alive=true;
    request<{slots:Slot[]}>(`/api/v1/ui/routes/${routeId}/slots`).then(r=>{if(alive){setSlots(r.slots);setSelected('');setMessage('');}}).catch(e=>{if(alive)setMessage(e.message);});
    return ()=>{alive=false;};
  },[isOpen,routeId]);
  if(!isOpen)return null;
  async function act(callback=false) {
    setBusy(true);setMessage('');
    try {
      const r=await request<{message:string}>(`/api/v1/ui/routes/${routeId}/${callback?'callback':'book'}`,callback?{}:{slot_id:selected});
      setMessage(r.message);await onSaved();setSlots([]);setSelected('');
    }catch(e){setMessage((e as Error).message);}finally{setBusy(false);}
  }
  return <div className="fixed inset-0 z-[60] bg-[#404040]/60 backdrop-blur-sm flex items-center justify-center p-4"><div className="bg-white text-[#404040] w-full max-w-md rounded-2xl shadow-2xl p-6 relative border border-[#e2e8f0]">
    <button aria-label="Закрыть запись" onClick={onClose} className="absolute top-4 right-4 text-lg">✕</button>
    <div className="mb-5"><span className="inline-block px-2.5 py-1 bg-[#13AB7B]/10 text-[#0f8e66] text-[11px] rounded-full">Учебное расписание</span><h3 className="font-bold text-lg mt-3">{slots[0]?.specialist || 'Запись на консультацию'}</h3><p className="text-xs mt-2">Действие сохранится в локальной БД. Реальная запись в клинику не выполняется.</p></div>
    {message&&<p role="status" className="my-4 rounded-xl border p-3 text-sm">{message}</p>}
    <div className="grid grid-cols-2 gap-2 mb-6">{slots.map(s=><button key={s.id} onClick={()=>setSelected(s.id)} className={`py-3 px-2 text-xs rounded-xl border ${selected===s.id?'border-[#13AB7B] bg-[#13AB7B]/10':'border-[#e2e8f0]'}`}>{new Date(s.date).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</button>)}</div>
    {!!slots.length&&<><button disabled={busy||!selected} onClick={()=>act()} className="w-full py-3 bg-[#13AB7B] text-white rounded-xl disabled:opacity-40 font-bold">Сохранить запись</button><button disabled={busy} onClick={()=>act(true)} className="w-full text-xs underline mt-4">Нет подходящего времени</button></>}
  </div></div>;
}
