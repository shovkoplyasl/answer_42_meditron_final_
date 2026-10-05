// src/components/PushNotificationSimulator.tsx
import React from 'react';

interface PushNotificationProps {
  message: string;
  isOpen: boolean;
  onClose: () => void;
  onClickNotification: () => void; // Переход при клике на пуш
}

export const PushNotificationSimulator: React.FC<PushNotificationProps> = ({
  message,
  isOpen,
  onClose,
  onClickNotification,
}) => {
  if (!isOpen) return null;

  return (
    <div
      onClick={onClickNotification}
      className="fixed top-5 right-5 z-[70] w-80 max-w-[90vw] bg-[#F6F8F7]/95 backdrop-blur-md text-white p-3.5 rounded-2xl shadow-2xl border border-[#13AB7B]/40 cursor-pointer hover:border-[#13AB7B] transition-all duration-200"
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-[#13AB7B] text-white rounded-md flex items-center justify-center text-[9px] font-black">
            СМ
          </div>
          <span className="text-[11px] font-semibold text-[#404040]/80">
            СМ-Клиника Пациент
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-white/50">сейчас</span>
          <button
            onClick={(e) => {
              e.stopPropagation(); // Чтобы не срабатывал клик по самому пушу
              onClose();
            }}
            className="text-black/50 hover:text-white text-xs px-1 transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Зафиксированная формулировка */}
      <div className="font-bold text-xs text-black mb-0.5">
        Уведомление
      </div>
      <div className="text-xs text-[#404040] leading-snug">
        {message}
      </div>
      <div className="mt-2 text-[10px] text-[#13AB7B] font-bold text-right flex items-center justify-end gap-1">
        <span>Открыть учебное расписание</span>
        <span>→</span>
      </div>
      <p className="mt-2 text-[10px] text-gray-600">Предпросмотр. Сохранено в БД; внешняя доставка не подключена.</p>
    </div>
  );
};
