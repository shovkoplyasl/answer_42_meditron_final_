import { useEffect, useState } from 'react';
import { request } from './api';
import type { Patient, HighlightComment, Session } from './api';
import ProtocolUpload from './components/ProtocolUpload';
import Analytics from './components/Analytics';

import DoctorLogin from './components/LogIn';
import { PushNotificationSimulator } from './components/PushNotificationSimulator';
import { PatientBookingModal } from './components/PatientBookingModal';

const ALL_DOCTOR_SPECIALTIES = [
  'Оперирующий гинеколог',
  'Маммолог / онколог',
  'Координатор',
  'Акушер-гинеколог',
  'Аллерголог-иммунолог',
  'Гастроэнтеролог',
  'Гематолог',
  'Дерматовенеролог',
  'Инфекционист',
  'Кардиолог',
  'Кардиохирург',
  'Невролог',
  'Нейрохирург',
  'Онколог',
  'Оториноларинголог (ЛОР)',
  'Офтальмолог',
  'Пульмонолог',
  'Ревматолог',
  'Сосудистый хирург',
  'Терапевт',
  'Травматолог-ортопед',
  'Уролог',
  'Хирург',
  'Эндокринолог'
];

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState<'patients' | 'analytics'>('patients');
  const [patients, setPatients] = useState<Patient[]>([]);

  const [isPushVisible, setIsPushVisible] = useState(false);
  const [isBookingModalOpen, setIsBookingModalOpen] = useState(false);

  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [selectedHighlightId, setSelectedHighlightId] = useState<string | null>(null);
  const [isEditingRoute, setIsEditingRoute] = useState(false);
  const [editedDoctorSpec, setEditedDoctorSpec] = useState('');
  const [editReason, setEditReason] = useState('');

  const [filterFio, setFilterFio] = useState('');
  const [filterUrgency, setFilterUrgency] = useState('Все');
  const [filterGender, setFilterGender] = useState('Все');
  const [filterBirthDate, setFilterBirthDate] = useState('');
  const [filterAttendingFio, setFilterAttendingFio] = useState('');
  const [filterAttendingSpec, setFilterAttendingSpec] = useState('Все');
  const [filterTargetSpec, setFilterTargetSpec] = useState('Все');
  const [filterInterference, setFilterInterference] = useState('Все');
  const [filterPushCount, setFilterPushCount] = useState('Все');
  const [filterMinCs, setFilterMinCs] = useState('0');
  const [filterStage, setFilterStage] = useState('Все');
  const [filterStatus, setFilterStatus] = useState('Все');

  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState('');
  const [uploadOpen,setUploadOpen] = useState(false);
  const [keyword,setKeyword] = useState('');
  const [noticeText,setNoticeText] = useState('');
  const [loadingSession,setLoadingSession] = useState(true);
  async function refresh() {
    const data=await request<Patient[]>('/api/v1/ui/patients');
    setPatients(data);
    setSelectedPatient(old=>old ? data.find(p=>p.id===old.id)||null : null);
  }
  useEffect(()=>{
    const expired=()=>{setIsAuthenticated(false);setPatients([]);setSelectedPatient(null);};
    window.addEventListener('session-expired',expired);
    request<Session>('/api/auth/session').then(async s=>{if(s.user){setIsAuthenticated(true);await refresh();}}).catch(e=>setMessage(e.message)).finally(()=>setLoadingSession(false));
    return ()=>window.removeEventListener('session-expired',expired);
  },[]);
  async function login(name:string,password:string) {
    await request<Session>('/api/auth/login',{username:name,password});
    setIsAuthenticated(true);await refresh();
  }
  async function logout() {
    try {await request('/api/auth/logout',{});setIsAuthenticated(false);setSelectedPatient(null);setPatients([]);}
    catch(e){setMessage((e as Error).message);}
  }
  async function importDemo() {
    setBusy(true);setMessage('Импорт и анализ протоколов…');
    try {const r=await request<{created:number}>('/api/v1/ui/import-demo',{});await refresh();setMessage(`Добавлено протоколов: ${r.created}`);}
    catch(e){setMessage((e as Error).message);} finally {setBusy(false);}
  }
  const handleTriggerPush = async () => {
    if(!selectedPatient?.routeId){setMessage('Сначала откройте протокол с подтверждённым маршрутом');return;}
    setBusy(true);
    try {const r=await request<{message:string;duplicate:boolean}>(`/api/v1/ui/routes/${selectedPatient.routeId}/notification`,{});
      setNoticeText(r.message);setIsPushVisible(true);await refresh();setMessage(r.duplicate?'Повтор не создан: уведомление уже есть':'Уведомление сохранено. Внешняя доставка не подключена');}
    catch(e){setMessage((e as Error).message);} finally {setBusy(false);}
  };
  const handlePushClick = () => {setIsPushVisible(false);setIsBookingModalOpen(true);};
  function downloadProtocol() {
    if(!selectedPatient)return;
    const url=URL.createObjectURL(new Blob([selectedPatient.protocolFullText],{type:'text/plain;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download=`protocol-${selectedPatient.protocolId}.txt`;link.click();URL.revokeObjectURL(url);
  }
  if(loadingSession)return <div className="p-8">Загрузка…</div>;
  if (!isAuthenticated) return <DoctorLogin onLogin={login}/>;

  const filteredPatients = patients.filter((p) => {
    const matchFio = p.fio.toLowerCase().includes(filterFio.toLowerCase()) || p.id.includes(filterFio);
    const matchUrgency = filterUrgency === 'Все' || p.urgency === filterUrgency;
    const matchGender = filterGender === 'Все' || p.gender === filterGender;
    const matchBirthDate = filterBirthDate === '' || p.birthDate.includes(filterBirthDate);
    const matchAttendingFio = p.attendingDoctorFio.toLowerCase().includes(filterAttendingFio.toLowerCase());
    const matchAttendingSpec = filterAttendingSpec === 'Все' || p.attendingDoctorSpec === filterAttendingSpec;
    const matchTargetSpec = filterTargetSpec === 'Все' || p.targetDoctorSpec === filterTargetSpec;
    const matchInterference = filterInterference === 'Все' || (filterInterference === 'Да' ? p.humanInterference : !p.humanInterference);
    const matchPushCount = filterPushCount === 'Все' || p.pushCount.toString() === filterPushCount;
    const matchCs = !Number(filterMinCs) || (p.csScore !== null && p.csScore >= Number(filterMinCs));
    const matchStage = filterStage === 'Все' || p.stage === filterStage;
    const matchStatus = filterStatus === 'Все' || p.status === filterStatus;

    return (
      keyword.split(',').map(x=>x.trim().toLocaleLowerCase()).filter(Boolean).every(x=>p.protocolFullText.toLocaleLowerCase().includes(x)) &&
      matchFio &&
      matchUrgency &&
      matchGender &&
      matchBirthDate &&
      matchAttendingFio &&
      matchAttendingSpec &&
      matchTargetSpec &&
      matchInterference &&
      matchPushCount &&
      matchCs &&
      matchStage &&
      matchStatus
    );
  });

  const handleOpenPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setSelectedHighlightId(null);
    setIsEditingRoute(false);
    setEditedDoctorSpec(patient.targetDoctorSpec);
    setEditReason('');
  };

  const handleSaveRoute = async () => {
    if(!selectedPatient)return;
    setBusy(true);
    try {await request('/api/v1/ui/route',{protocol_id:selectedPatient.protocolId,specialist:editedDoctorSpec,reason:editReason});await refresh();setIsEditingRoute(false);setMessage('Изменение маршрута сохранено в БД');}
    catch(e){setMessage((e as Error).message);} finally {setBusy(false);}
  };

  const renderInteractiveProtocol = (patient: Patient) => {
    const text = patient.protocolFullText;
    const parts: { text: string; isHighlight: boolean; highlightObj?: HighlightComment }[] = [];

    let currentIdx = 0;
    const sortedHighlights = [...patient.highlights].sort(
      (a, b) => text.indexOf(a.text) - text.indexOf(b.text)
    );

    sortedHighlights.forEach((h) => {
      const idx = text.indexOf(h.text, currentIdx);
      if (idx !== -1) {
        if (idx > currentIdx) {
          parts.push({ text: text.substring(currentIdx, idx), isHighlight: false });
        }
        parts.push({ text: h.text, isHighlight: true, highlightObj: h });
        currentIdx = idx + h.text.length;
      }
    });

    if (currentIdx < text.length) {
      parts.push({ text: text.substring(currentIdx), isHighlight: false });
    }

    return (
      <div className="text-xs text-[#404040] leading-relaxed font-mono whitespace-pre-wrap">
        {parts.map((part, index) => {
          if (!part.isHighlight || !part.highlightObj) {
            return <span key={index}>{part.text}</span>;
          }
          const isSelected = selectedHighlightId === part.highlightObj.id;
          return (
            <mark
              key={index}
              onClick={() => setSelectedHighlightId(part.highlightObj!.id)}
              className={`cursor-pointer px-1 py-0.5 rounded font-bold transition-all border ${
                isSelected
                  ? 'bg-[#13AB7B] text-white border-[#0f8e66] ring-2 ring-[#13AB7B]/30'
                  : 'bg-[#13AB7B]/20 hover:bg-[#13AB7B]/30 text-[#404040] border-[#13AB7B]/40'
              }`}
              title="Нажмите, чтобы просмотреть комментарий"
            >
              {part.text}
            </mark>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#F6F8F7] font-sans text-[#404040]">
      {/* Шапка в фирменном тёмном цвете #404040 с логотипом #13AB7B */}
      <header className="bg-[#404040] text-white px-6 py-4 flex justify-between items-center shadow-md border-b border-[#e2e8f0]/20">
        <div className="flex items-center gap-3">
          <div className="bg-[#13AB7B] text-white font-black px-3 py-1 rounded-lg text-lg tracking-wider">СМ</div>
          <h1 className="text-xl font-bold tracking-wide">Панель врача-координатора</h1>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setUploadOpen(true)}
            className="bg-[#13AB7B]/20 hover:bg-[#13AB7B]/30 text-[#13AB7B] border border-[#13AB7B]/40 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <span>🔔</span>
            <span>Добавить протокол</span>
          </button>

          <div className="text-sm bg-white/10 px-3 py-1.5 rounded-lg border border-white/20 flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#13AB7B] rounded-full"></span>
            <span>Врач-координатор: <strong>Координатор</strong></span>
          </div>

          <button
            onClick={logout}
            className="bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/30 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            Выйти
          </button>
        </div>
      </header>

      {/* Горизонтальные вкладки */}
      <div className="bg-[#e2e8f0]/60 pt-3 px-6 border-b border-[#e2e8f0] flex gap-2">
        <button
          onClick={() => setActiveTab('patients')}
          className={`px-6 py-2.5 font-semibold text-sm rounded-t-lg transition-all ${
            activeTab === 'patients'
              ? 'bg-white text-[#13AB7B] shadow-sm border-t-2 border-[#13AB7B]'
              : 'bg-white/50 text-[#404040]/70 hover:bg-white/80'
          }`}
        >
          Список пациентов ({filteredPatients.length})
        </button>

        <button
          onClick={() => setActiveTab('analytics')}
          className={`px-6 py-2.5 font-semibold text-sm rounded-t-lg transition-all ${
            activeTab === 'analytics'
              ? 'bg-white text-[#13AB7B] shadow-sm border-t-2 border-[#13AB7B]'
              : 'bg-white/50 text-[#404040]/70 hover:bg-white/80'
          }`}
        >
          Аналитика
        </button>
      </div>

      <main className="p-6">
        <div className="mb-4 flex flex-wrap items-center gap-3 text-xs">
          <button onClick={importDemo} disabled={busy} className="bg-white border rounded-xl px-4 py-2 disabled:opacity-50">{busy?'Выполняется…':'Импортировать 89 протоколов'}</button>
          <button onClick={()=>refresh().catch(e=>setMessage(e.message))} className="bg-white border rounded-xl px-4 py-2">Обновить</button>
          <span>Данные из БД · ФИО и демографические данные не переданы · Расписание учебное</span>
        </div>
        {message && <div role="status" className="mb-4 bg-white border border-[#13AB7B]/30 rounded-xl p-3 text-sm">{message}</div>}

        {/* ================= ВКЛАДКА: СПИСОК ПАЦИЕНТОВ ================= */}
        {activeTab === 'patients' && (
          <div className="bg-white rounded-b-xl rounded-tr-xl p-6 shadow-sm border border-[#e2e8f0]">
            {/* Блок фильтров */}
            <div className="bg-[#F6F8F7] p-4 rounded-xl border border-[#e2e8f0] mb-6 space-y-3">
              <div className="text-xs font-bold text-[#404040]/70 uppercase tracking-wider">Панель фильтров</div>
              <input aria-label="Ключевые слова" value={keyword} onChange={e=>setKeyword(e.target.value)} placeholder="Ключевые слова в протоколе через запятую (все слова)" className="w-full border rounded-xl px-3 py-2 text-sm"/>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Поиск ФИО / ID</label>
                  <input
                    type="text"
                    placeholder="Иванов или #10293..."
                    value={filterFio}
                    onChange={(e) => setFilterFio(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] bg-white rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Срочность</label>
                  <select
                    value={filterUrgency}
                    onChange={(e) => setFilterUrgency(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все</option>
                    <option value="Критическая">Критическая</option>
                    <option value="Высокая">Высокая</option>
                    <option value="Средняя">Средняя</option>
                    <option value="Низкая">Низкая</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Пол</label>
                  <select
                    value={filterGender}
                    onChange={(e) => setFilterGender(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все</option>
                    <option value="М">Мужской (М)</option>
                    <option value="Ж">Женский (Ж)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Дата рождения</label>
                  <input
                    type="text"
                    placeholder="ДД.ММ.ГГГГ"
                    value={filterBirthDate}
                    onChange={(e) => setFilterBirthDate(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] bg-white rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">ФИО лечащего врача</label>
                  <input
                    type="text"
                    placeholder="ФИО врача..."
                    value={filterAttendingFio}
                    onChange={(e) => setFilterAttendingFio(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] bg-white rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Спец. лечащего врача</label>
                  <select
                    value={filterAttendingSpec}
                    onChange={(e) => setFilterAttendingSpec(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все специальности</option>
                    {ALL_DOCTOR_SPECIALTIES.map((spec) => (
                      <option key={spec} value={spec}>{spec}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Спец. врача (маршрут)</label>
                  <select
                    value={filterTargetSpec}
                    onChange={(e) => setFilterTargetSpec(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все специальности</option>
                    {ALL_DOCTOR_SPECIALTIES.map((spec) => (
                      <option key={spec} value={spec}>{spec}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Вмешательство человека</label>
                  <select
                    value={filterInterference}
                    onChange={(e) => setFilterInterference(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все</option>
                    <option value="Да">Да (Было)</option>
                    <option value="Нет">Нет (Автомат)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Кол-во пушей</label>
                  <select
                    value={filterPushCount}
                    onChange={(e) => setFilterPushCount(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все</option>
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Мин. CS уверенность (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={filterMinCs}
                    onChange={(e) => setFilterMinCs(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] bg-white rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Этап маршрута</label>
                  <select
                    value={filterStage}
                    onChange={(e) => setFilterStage(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все этапы</option>
                    <option value="PUSH отправлен">Уведомление создано</option>
                    <option value="Запись предложена">Запись предложена</option>
                    <option value="Запись отклонена">Запись отклонена</option>
                    <option value="Запись зарегистрирована">Запись зарегистрирована</option>
                    <option value="На приёме">На приёме</option>
                    <option value="Приём завершён">Приём завершён</option>
                    <option value="Протокол загружен">Протокол загружен</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#404040] mb-1">Статус случая</label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#e2e8f0] rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                  >
                    <option value="Все">Все статусы</option>
                    <option value="Новое">Новое</option>
                    <option value="В работе">В работе</option>
                    <option value="Требует консилиума">Требует консилиума</option>
                    <option value="Закрыто">Закрыто</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Таблица */}
            <div className="overflow-x-auto rounded-xl border border-[#e2e8f0]">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F6F8F7] border-b border-[#e2e8f0] text-[#404040] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="p-3">Срочность</th>
                    <th className="p-3">ID</th>
                    <th className="p-3">ФИО пациента</th>
                    <th className="p-3">Пол</th>
                    <th className="p-3">Дата рождения</th>
                    <th className="p-3">ФИО лечащего врача</th>
                    <th className="p-3">Спец. лечащего врача</th>
                    <th className="p-3">Направляемый врач</th>
                    <th className="p-3 text-center">Вмешательство</th>
                    <th className="p-3 text-center">Пуши</th>
                    <th className="p-3 text-center">CS</th>
                    <th className="p-3">Этап маршрута</th>
                    <th className="p-3">Статус случая</th>
                    <th className="p-3 text-center">Действие</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e2e8f0]">
                  {filteredPatients.map((p) => {
                    const isUrgent = p.urgency === 'Критическая' || p.urgency === 'Высокая';
                    return (
                      <tr
                        key={p.id}
                        className={`transition-colors ${
                          isUrgent
                            ? 'bg-red-50 hover:bg-red-100/80 border-l-4 border-l-red-600'
                            : 'hover:bg-[#F6F8F7]'
                        }`}
                      >
                        <td className="p-3 whitespace-nowrap">
                          <span
                            className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                              p.urgency === 'Критическая'
                                ? 'bg-red-200 text-red-900 border border-red-300'
                                : p.urgency === 'Высокая'
                                ? 'bg-red-100 text-red-800 border border-red-200'
                                : 'bg-[#e2e8f0] text-[#404040]'
                            }`}
                          >
                            {p.urgency}
                          </span>
                        </td>
                        <td className="p-3 font-mono font-bold text-[#404040]/80">#{p.id}</td>
                        <td className="p-3 font-semibold text-[#404040] whitespace-nowrap">{p.fio}</td>
                        <td className="p-3 font-medium text-[#404040]">{p.gender}</td>
                        <td className="p-3 whitespace-nowrap text-[#404040]/80">{p.birthDate}</td>
                        <td className="p-3 whitespace-nowrap text-[#404040]">{p.attendingDoctorFio}</td>
                        <td className="p-3 whitespace-nowrap text-[#404040]/70">{p.attendingDoctorSpec}</td>
                        <td className="p-3 font-bold text-[#13AB7B] whitespace-nowrap">{p.targetDoctorSpec}</td>
                        <td className="p-3 text-center">
                          {p.humanInterference ? (
                            <span className="bg-[#13AB7B]/20 text-[#0f8e66] font-bold px-2 py-0.5 rounded text-[11px]">Да</span>
                          ) : (
                            <span className="bg-[#e2e8f0] text-[#404040]/60 px-2 py-0.5 rounded text-[11px]">Нет</span>
                          )}
                        </td>
                        <td className="p-3 text-center font-bold">{p.pushCount}</td>
                        <td className="p-3 text-center font-black text-[#13AB7B]">{p.csScore === null ? '—' : `${p.csScore}%`}</td>
                        <td className="p-3 whitespace-nowrap">
                          <span className="bg-[#13AB7B]/10 text-[#0f8e66] px-2 py-1 rounded border border-[#13AB7B]/20 text-[11px] font-medium">
                            {p.stage}
                          </span>
                        </td>
                        <td className="p-3 whitespace-nowrap">
                          <span className="bg-amber-100 text-amber-900 px-2 py-1 rounded text-[11px] font-semibold">
                            {p.status}
                          </span>
                        </td>
                        <td className="p-3 text-center whitespace-nowrap">
                          <button
                            onClick={() => handleOpenPatient(p)}
                            className="bg-[#13AB7B] hover:bg-[#0f8e66] text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors shadow-sm"
                          >
                            Открыть
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ================= ВКЛАДКА: АНАЛИТИКА ================= */}
        {activeTab === 'analytics' && <Analytics patients={patients}/>}
      </main>

      {/* МОДАЛЬНОЕ ОКНО КАРТОЧКИ ПАЦИЕНТА */}
      {selectedPatient && (
        <div className="fixed inset-0 bg-[#404040]/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-3xl max-w-5xl w-full p-8 shadow-2xl border border-[#e2e8f0] overflow-hidden relative">
            
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold text-[#404040] mb-1">{selectedPatient.fio}</h2>
                <div className="text-xs text-[#404040]/80 font-medium">
                  Пол: <strong>{selectedPatient.gender}</strong> | ДР: <strong>{selectedPatient.birthDate}</strong> | Лечащий врач: <strong>{selectedPatient.attendingDoctorFio}</strong> ({selectedPatient.attendingDoctorSpec})
                </div>
              </div>

              <button
                onClick={downloadProtocol}
                className="bg-[#13AB7B]/10 hover:bg-[#13AB7B]/20 text-[#0f8e66] font-semibold text-xs px-4 py-2 rounded-xl border border-[#13AB7B]/30 transition-colors"
              >
                Скачать протокол
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <div className="space-y-2">
                <div className="text-xs font-bold text-[#404040]">
                  Протокол исследования (нажмите на выделение для просмотра комментария)
                </div>

                <div className="bg-[#F6F8F7] border border-[#e2e8f0] rounded-2xl p-4 h-full min-h-65 max-h-90 overflow-y-auto">
                  {renderInteractiveProtocol(selectedPatient)}
                </div>
              </div>

              <div className="space-y-4">
                <div className="bg-[#F6F8F7] border border-[#e2e8f0] rounded-2xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-[#404040]">Уверенность модели (CS)</span>
                    <span className="text-sm font-black text-[#13AB7B]">{selectedPatient.csScore === null ? 'Не рассчитывается' : `${selectedPatient.csScore ?? 0}%`}</span>
                  </div>
                  <div className="w-full bg-[#e2e8f0] h-2.5 rounded-full overflow-hidden">
                    <div
                      className="bg-[#13AB7B] h-full rounded-full transition-all duration-500"
                      style={{ width: `${selectedPatient.csScore === null ? 'Не рассчитывается' : `${selectedPatient.csScore ?? 0}%`}` }}
                    ></div>
                  </div>
                </div>

                <div className="bg-[#13AB7B]/10 border border-[#13AB7B]/20 rounded-2xl p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-[#0f8e66]">
                      {selectedHighlightId ? 'Комментарий к выбранному фрагменту:' : 'Результат анализа протокола:'}
                    </span>
                    {selectedHighlightId && (
                      <button
                        onClick={() => setSelectedHighlightId(null)}
                        className="text-[11px] text-[#13AB7B] hover:underline font-bold"
                      >
                        Показать все комментарии
                      </button>
                    )}
                  </div>

                  {!selectedHighlightId ? (
                    <div className="space-y-2 text-xs text-[#404040]">
                      <p className="leading-relaxed border-b border-[#13AB7B]/20 pb-2">{selectedPatient.aiComment}</p>
                      <div className="space-y-1.5 pt-1">
                        <div className="text-[11px] font-bold text-[#0f8e66] uppercase">Выделенные ключевые слова:</div>
                        {selectedPatient.highlights.map((h) => (
                          <div key={h.id} className="bg-white p-2 rounded-lg border border-[#13AB7B]/20">
                            <span className="font-bold underline text-[#13AB7B]">{h.text}:</span> {h.comment}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-[#404040] space-y-1">
                      {selectedPatient.highlights
                        .filter((h) => h.id === selectedHighlightId)
                        .map((h) => (
                          <div key={h.id} className="bg-white p-2.5 rounded-xl border border-[#13AB7B]/30">
                            <div className="font-bold text-[#13AB7B] mb-1">Фрагмент: "{h.text}"</div>
                            <div>{h.comment}</div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>

                {!isEditingRoute ? (
                  <div className="bg-[#F6F8F7] border border-[#e2e8f0] rounded-2xl p-4">
                    <div className="text-[10px] uppercase tracking-wider font-bold text-[#404040]/50 mb-1">
                      ПЕРВОСТЕПЕННЫЙ МАРШРУТ (ВРАЧ)
                    </div>
                    <div className="text-base font-bold text-[#404040]">
                      {selectedPatient.targetDoctorSpec}
                    </div>
                  </div>
                ) : (
                  <div className="bg-[#13AB7B]/5 border border-[#13AB7B]/30 rounded-2xl p-4 space-y-3">
                    <div className="text-xs font-bold text-[#0f8e66]">Выбор врача из общего списка врачей:</div>
                    <select
                      value={editedDoctorSpec}
                      onChange={(e) => setEditedDoctorSpec(e.target.value)}
                      className="w-full p-2 border border-[#13AB7B]/40 rounded-xl text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#13AB7B] font-semibold"
                    >
                      {ALL_DOCTOR_SPECIALTIES.map((spec) => (
                        <option key={spec} value={spec}>
                          {spec}
                        </option>
                      ))}
                    </select>
                    <textarea
                      placeholder="Укажите причину перенаправления..."
                      value={editReason}
                      onChange={(e) => setEditReason(e.target.value)}
                      className="w-full p-2 border border-[#13AB7B]/40 rounded-xl text-xs bg-white h-16 focus:outline-none focus:ring-1 focus:ring-[#13AB7B]"
                    ></textarea>
                  </div>
                )}

              </div>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-[#e2e8f0]">
              <button
                onClick={handleTriggerPush}
                disabled={busy || !selectedPatient.canNotify}
                className="px-4 py-2.5 bg-[#13AB7B]/10 hover:bg-[#13AB7B]/20 text-[#0f8e66] border border-[#13AB7B]/30 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
              >
                <span>🔔</span>
                <span>Создать уведомление</span>
              </button>

              <div className="flex gap-3">
                <button
                  onClick={() => setSelectedPatient(null)}
                  className="px-6 py-2.5 bg-[#F6F8F7] hover:bg-[#e2e8f0] text-[#404040] rounded-xl text-xs font-bold transition-colors"
                >
                  Свернуть
                </button>

                {!isEditingRoute ? (
                  <button
                    onClick={() => setIsEditingRoute(true)}
                    className="px-6 py-2.5 bg-[#13AB7B] hover:bg-[#0f8e66] text-white rounded-xl text-xs font-bold transition-colors shadow-sm"
                  >
                    Редактировать маршрут
                  </button>
                ) : (
                  <button
                    onClick={handleSaveRoute}
                    disabled={busy || editReason.trim().length<3}
                    className="px-6 py-2.5 bg-[#13AB7B] hover:bg-[#0f8e66] text-white rounded-xl text-xs font-bold transition-colors shadow-sm"
                  >
                    Сохранить маршрут
                  </button>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

      {uploadOpen && <ProtocolUpload onClose={()=>setUploadOpen(false)} onSaved={refresh}/>}
      <PushNotificationSimulator
        isOpen={isPushVisible}
        message={noticeText}
        onClose={() => setIsPushVisible(false)}
        onClickNotification={handlePushClick}
      />

      <PatientBookingModal
        isOpen={isBookingModalOpen}
        routeId={selectedPatient?.routeId ?? null}
        onSaved={refresh}
        onClose={() => setIsBookingModalOpen(false)}
      />
    </div>
  );
}