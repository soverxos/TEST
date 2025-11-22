import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Locale = 'en' | 'ru' | 'ua';

type Translations = {
  [key: string]: string;
};

type I18nContextType = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  availableLocales: Locale[];
};

const I18nContext = createContext<I18nContextType | undefined>(undefined);

// Загружаем переводы
const loadTranslations = async (locale: Locale): Promise<Translations> => {
  try {
    const response = await fetch(`/locales/${locale}.json`);
    if (!response.ok) {
      throw new Error(`Failed to load translations for ${locale}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error loading translations for ${locale}:`, error);
    // Fallback на английский
    if (locale !== 'en') {
      return loadTranslations('en');
    }
    return {};
  }
};

export const useI18n = () => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
};

export const I18nProvider = ({ children }: { children: ReactNode }) => {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const saved = localStorage.getItem('web_locale') as Locale;
    return saved && ['en', 'ru', 'ua'].includes(saved) ? saved : 'en';
  });

  const [translations, setTranslations] = useState<Translations>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTranslations(locale).then((translations) => {
      console.log(`[I18n] Loaded translations for ${locale}:`, translations);
      setTranslations(translations);
      setLoading(false);
    }).catch((error) => {
      console.error(`[I18n] Error loading translations for ${locale}:`, error);
      setLoading(false);
    });
  }, [locale]);

  useEffect(() => {
    localStorage.setItem('web_locale', locale);
  }, [locale]);

  const setLocale = (newLocale: Locale) => {
    setLoading(true);
    setLocaleState(newLocale);
  };

  const t = (key: string, params?: Record<string, string | number>): string => {
    // Поддержка вложенных ключей через точку (например, "sidebar.home")
    const keys = key.split('.');
    let text: any = translations;
    
    for (const k of keys) {
      if (text && typeof text === 'object' && k in text) {
        text = text[k];
      } else {
        // Если ключ не найден, логируем и возвращаем сам ключ
        if (Object.keys(translations).length > 0) {
          console.warn(`[I18n] Translation key not found: "${key}" for locale "${locale}"`);
        }
        return key;
      }
    }
    
    // Если text не строка, возвращаем ключ
    if (typeof text !== 'string') {
      console.warn(`[I18n] Translation value is not a string for key "${key}":`, text);
      return key;
    }
    
    // Заменяем параметры в тексте
    if (params) {
      Object.entries(params).forEach(([paramKey, paramValue]) => {
        text = text.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramValue));
      });
    }
    
    return text;
  };

  const availableLocales: Locale[] = ['en', 'ru', 'ua'];

  if (loading && Object.keys(translations).length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <I18nContext.Provider value={{ locale, setLocale, t, availableLocales }}>
      {children}
    </I18nContext.Provider>
  );
};

