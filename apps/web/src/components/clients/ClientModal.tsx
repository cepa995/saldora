'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import type {
  BookkeepingSystem,
  ClientCreate,
  ClientResponse,
  ClientUpdate,
  LegalForm,
} from '@/lib/types/client';

interface Props {
  client: ClientResponse | null;
  saving: boolean;
  onSave: (data: ClientCreate | ClientUpdate) => void;
  onClose: () => void;
}

const LEGAL_FORM_OPTIONS: LegalForm[] = ['DOO', 'preduzetnik', 'paušalac', 'drugo'];
const BOOKKEEPING_OPTIONS: BookkeepingSystem[] = ['dvojno', 'prosto'];

export function ClientModal({ client, saving, onSave, onClose }: Props) {
  const t = useTranslations('clients');
  const tc = useTranslations('common');

  const [name, setName] = useState(client?.name || '');
  const [pib, setPib] = useState(client?.pib || '');
  const [mb, setMb] = useState(client?.mb || '');
  const [address, setAddress] = useState(client?.address || '');
  const [city, setCity] = useState(client?.city || '');
  const [postalCode, setPostalCode] = useState(client?.postal_code || '');
  const [email, setEmail] = useState(client?.contact_email || '');
  const [phone, setPhone] = useState(client?.contact_phone || '');
  const [legalForm, setLegalForm] = useState<LegalForm | ''>(client?.legal_form ?? '');
  const [bookkeeping, setBookkeeping] = useState<BookkeepingSystem | ''>(
    client?.bookkeeping_system ?? '',
  );
  const [notes, setNotes] = useState(client?.notes || '');

  // DOO implies dvojno by Zakon o računovodstvu — we don't make the agency
  // pick bookkeeping_system for DOOs (mirrors the server-side matrix in
  // app.services.hospitality_forms.required_forms).
  const bookkeepingDisabled = legalForm === 'DOO' || legalForm === 'paušalac';

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data: ClientCreate | ClientUpdate = {
      name,
      pib,
      mb: mb || undefined,
      address: address || undefined,
      city: city || undefined,
      postal_code: postalCode || undefined,
      contact_email: email || undefined,
      contact_phone: phone || undefined,
      legal_form: legalForm || undefined,
      bookkeeping_system: bookkeepingDisabled ? undefined : bookkeeping || undefined,
      notes: notes || undefined,
    };
    onSave(data);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            {client ? t('editClient') : t('createClient')}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('name')} *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('pib')} *</label>
              <input
                type="text"
                value={pib}
                onChange={(e) => setPib(e.target.value)}
                required
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('mb')}</label>
              <input
                type="text"
                value={mb}
                onChange={(e) => setMb(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('address')}</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('city')}</label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('postalCode')}</label>
              <input
                type="text"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('contactEmail')}</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('contactPhone')}</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>

          {/* Hospitality classification — drives the obligation matrix on
              the Izveštaji tab (kalkulacija, KEP, šank lista, cenovnik,
              popis). Both fields are nullable; agency sets them at first
              review. */}
          <div className="border-t border-gray-100 pt-4">
            <div className="flex items-baseline justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-800">{t('classificationTitle')}</h3>
              <span className="text-[11px] text-gray-500">{t('classificationHint')}</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('legalForm')}</label>
                <select
                  value={legalForm}
                  onChange={(e) => setLegalForm(e.target.value as LegalForm | '')}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 bg-white"
                >
                  <option value="">{t('unsetOption')}</option>
                  {LEGAL_FORM_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {t(`legalFormOption.${opt}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('bookkeepingSystem')}
                </label>
                <select
                  value={bookkeepingDisabled ? '' : bookkeeping}
                  disabled={bookkeepingDisabled}
                  onChange={(e) => setBookkeeping(e.target.value as BookkeepingSystem | '')}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 bg-white disabled:bg-gray-50 disabled:text-gray-400"
                >
                  <option value="">{t('unsetOption')}</option>
                  {BOOKKEEPING_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {t(`bookkeepingOption.${opt}`)}
                    </option>
                  ))}
                </select>
                {legalForm === 'DOO' && (
                  <p className="text-[11px] text-gray-500 mt-1">{t('dooImpliesDvojno')}</p>
                )}
                {legalForm === 'paušalac' && (
                  <p className="text-[11px] text-gray-500 mt-1">{t('pausalacOutOfScope')}</p>
                )}
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('notes')}</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 resize-none"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              {tc('cancel')}
            </button>
            <button
              type="submit"
              disabled={saving || !name || !pib}
              className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? tc('saving') : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
