import { useState } from 'react';
import type { Patient } from '../api';
export default function Analytics({patients}:{patients:Patient[]}) {
  const [start,setStart]=useState('');const [end,setEnd]=useState('');
  const rows=patients.filter(p=>(!start || p.protocolDateISO.slice(0,10)>=start) && (!end || p.protocolDateISO.slice(0,10)<=end));
  const groups=(field:'stage'|'targetDoctorSpec')=>Object.entries(rows.reduce<Record<string,number>>((a,p)=>{a[p[field]]=(a[p[field]]||0)+1;return a;},{}));
  const adjusted=rows.filter(p=>p.humanInterference).length;
  return <div className="bg-white rounded-b-xl rounded-tr-xl p-6 shadow-sm border border-[#e2e8f0] space-y-6">
    <div className="flex flex-wrap items-center gap-3"><h2 className="text-lg font-bold mr-auto">Аналитика по данным БД</h2><label className="text-xs">С <input type="date" value={start} onChange={e=>setStart(e.target.value)} className="border rounded-lg p-2"/></label><label className="text-xs">По <input type="date" value={end} onChange={e=>setEnd(e.target.value)} className="border rounded-lg p-2"/></label></div>
    <p className="text-xs text-gray-500">Период относится к дате протокола. В выборке {rows.length} протоколов; сведения об исходах лечения и внешней доставке отсутствуют.</p>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">{(['stage','targetDoctorSpec'] as const).map(field=><div key={field} className="bg-[#F6F8F7] border border-[#e2e8f0] rounded-2xl p-5 space-y-4"><h3 className="font-bold text-sm">{field==='stage'?'Текущие этапы':'Направления по специалистам'}</h3>{groups(field).map(([label,count])=><div key={label}><div className="flex justify-between text-xs mb-2"><span>{label}</span><strong>{count}</strong></div><div className="h-3 rounded-full bg-[#e2e8f0]"><div className="h-full rounded-full bg-[#13AB7B]" style={{width:`${rows.length ? count/rows.length*100:0}%`}}/></div></div>)}{!rows.length&&<p>Нет данных за период</p>}</div>)}
      <div className="bg-[#F6F8F7] border border-[#e2e8f0] rounded-2xl p-5"><h3 className="font-bold text-sm">Ручная коррекция маршрута</h3><div className="text-3xl font-black my-4">{rows.length?Math.round(adjusted/rows.length*100):0}%</div><p className="text-sm">{adjusted} из {rows.length} протоколов</p></div>
      <div className="bg-[#F6F8F7] border border-[#e2e8f0] rounded-2xl p-5"><h3 className="font-bold text-sm">Срочность и уверенность</h3><p className="text-sm mt-4">Текущий алгоритм не рассчитывает вероятность и клиническую срочность. Проценты не подставляются.</p></div>
    </div>
  </div>;
}
