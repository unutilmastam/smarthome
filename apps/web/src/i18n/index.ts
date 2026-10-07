import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import uz from "./locales/uz.json";
import ru from "./locales/ru.json";
import en from "./locales/en.json";

export const LANGUAGES = ["uz", "ru", "en"] as const;
export type Lang = (typeof LANGUAGES)[number];

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem("sh.lang");
    if (saved && (LANGUAGES as readonly string[]).includes(saved)) return saved as Lang;
  } catch { /* ignore */ }
  return "uz";
}

void i18n.use(initReactI18next).init({
  resources: { uz: { translation: uz }, ru: { translation: ru }, en: { translation: en } },
  lng: initialLang(),
  fallbackLng: "uz",
  interpolation: { escapeValue: false },
});

export function setLanguage(lang: Lang) {
  try { localStorage.setItem("sh.lang", lang); } catch { /* ignore */ }
  void i18n.changeLanguage(lang);
  document.documentElement.lang = lang;
}

export default i18n;
