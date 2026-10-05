import React, { useState } from 'react';

// 1. Объявляем интерфейс пропсов (принимаем функцию отмена/входа)
interface DoctorLoginProps {
  onLogin: (login: string, password: string) => Promise<void>;
}

export default function DoctorLogin({ onLogin }: DoctorLoginProps) {
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);

  // 2. Обработчик нажатия на кнопку "Продолжить"
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    setBusy(true);setError('');
    try {await onLogin(login,password);} catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row font-sans bg-white">
      {/* Левая часть (Брендинг) */}
      <div className="hidden md:flex w-[45%] bg-[#00a86b] flex-col items-center justify-center p-10 relative overflow-hidden text-center text-white">
        <div className="flex flex-col items-center mb-8 z-10">
          <div className="w-16 h-16 border-2 border-white rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold tracking-wide">СМ-Клиника</h1>
        </div>

        <p className="text-sm font-medium z-10 max-w-70 leading-relaxed">
          С помощью обновлённого личного кабинета управлять расписанием стало гораздо проще!
        </p>

        <div className="mt-12 z-10">
          <div className="w-64 h-64 bg-white/10 rounded-full flex items-center justify-center backdrop-blur-sm border border-white/20">
            <span className="text-white/50 text-sm">Место для 3D иллюстрации</span>
          </div>
        </div>

        <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-white opacity-5 rounded-full blur-3xl"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-white opacity-5 rounded-full blur-3xl"></div>
      </div>

      {/* Правая часть (Форма) */}
      <div className="flex-1 flex flex-col relative h-screen">
        <div className="flex justify-between items-center p-6 text-sm font-medium text-gray-500">
          <button type="button" className="flex items-center hover:text-gray-800 transition-colors">
            <span className="mr-2">←</span> Вернуться назад
          </button>
          <button type="button" className="flex items-center hover:text-gray-800 transition-colors">
            <span className="mr-2 text-lg">?</span> Помощь
          </button>
        </div>

        <div className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-100">
            <h2 className="text-2xl font-bold text-[#1f2937] text-center mb-8">
              Войдите в личный кабинет врача
            </h2>

            {/* Привязываем handleSubmit к форме */}
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <p className="text-xs text-gray-500">Локальный стенд: логин и пароль в файле local-data/LOCAL_ACCOUNTS.txt.</p>
              {error && <p role="alert" className="text-red-600 text-sm">{error}</p>}
              <input
                type="text"
                required autoComplete="username" aria-label="Логин"
                placeholder="Логин (Табельный номер)"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                className="w-full px-5 py-4 bg-[#f3f4f6] text-gray-800 rounded-xl outline-none focus:ring-2 focus:ring-[#00a86b]/50 transition-all placeholder-gray-400"
              />

              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required autoComplete="current-password" aria-label="Пароль"
                  placeholder="Пароль"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-5 py-4 bg-[#f3f4f6] text-gray-800 rounded-xl outline-none focus:ring-2 focus:ring-[#00a86b]/50 transition-all placeholder-gray-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>

              <div className="flex justify-start mb-2">
                <button type="button" className="text-sm text-gray-400 hover:text-gray-600">
                  Забыли пароль?
                </button>
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full bg-[#00a86b] hover:bg-[#00965f] text-white py-4 px-6 rounded-xl font-semibold flex justify-between items-center transition-colors shadow-lg shadow-[#00a86b]/20"
              >
                <span>{busy?'Вход…':'Продолжить'}</span>
                <span>→</span>
              </button>

              <p className="text-xs text-gray-400 mt-4 text-center leading-relaxed">
                Принимаю условия <a href="#" className="text-[#00a86b] hover:underline">Оферты</a>, ознакомлен(а) с <a href="#" className="text-[#00a86b] hover:underline">Политикой в отношении обработки персональных данных</a>
              </p>
            </form>
          </div>
        </div>

        <div className="absolute bottom-0 w-full bg-[#f9fafb] p-4 flex flex-col md:flex-row justify-between items-center border-t border-gray-100 text-[10px] text-gray-400">
          <p>© 2002–2026 ООО «СМ-Клиника». Лицензия № ЛО-77-01-018779 от 19 сентября 2019 г.</p>
          <div className="flex gap-2 mt-2 md:mt-0">
            <div className="h-8 w-24 bg-gray-200 rounded flex items-center justify-center">RuStore</div>
            <div className="h-8 w-24 bg-gray-200 rounded flex items-center justify-center">App Store</div>
            <div className="h-8 w-24 bg-gray-200 rounded flex items-center justify-center">Google Play</div>
            <div className="h-8 w-24 bg-gray-200 rounded flex items-center justify-center">AppGallery</div>
          </div>
        </div>
      </div>
    </div>
  );
}
