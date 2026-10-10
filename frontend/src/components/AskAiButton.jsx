// "Ask AI" button: builds a ready-made question in the shop's language and opens the advisor page for that product.
//   <AskAiButton productId={7} productName="Rice" questionKey="price" />      questionKey: price | forecast | recommendation
import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const QUESTIONS = {
  en: {
    price: (n) => `Explain the price I paid for ${n}. Is it fair?`,
    forecast: (n) => `Explain the price forecast for ${n}.`,
    recommendation: (n) => `Why this recommendation for ${n}?`,
  },
  hi: {
    price: (n) => `${n} का मेरा भाव समझाइए। क्या यह सही है?`,
    forecast: (n) => `${n} का भाव अनुमान समझाइए।`,
    recommendation: (n) => `${n} के लिए यह सलाह क्यों दी गई?`,
  },
  mr: {
    price: (n) => `${n} साठी मी दिलेला भाव समजवा. तो वाजवी आहे का?`,
    forecast: (n) => `${n} च्या भावाचा अंदाज समजवा.`,
    recommendation: (n) => `${n} साठी ही सूचना का दिली?`,
  },
}
const LABEL = { en: 'Ask AI', hi: 'AI से पूछें', mr: 'AI ला विचारा' }

export function buildQuestion(language, key, productName) {
  const set = QUESTIONS[language] || QUESTIONS.en
  return (set[key] || set.price)(productName)
}

export default function AskAiButton({ productId, productName, questionKey = 'price', className = '', label }) {
  const navigate = useNavigate()
  const { shop } = useAuth()
  const language = localStorage.getItem('vyapariAdvisorLang') || shop?.language || 'en'
  const go = () => {
    const q = buildQuestion(language, questionKey, productName)
    navigate(`/advisor?productId=${productId}&q=${encodeURIComponent(q)}`)
  }
  return (
    <button onClick={go} className={`flex items-center gap-1.5 rounded-[8px] border border-secondary/40 bg-card px-3 py-1.5 text-[13px] font-medium text-secondary hover:bg-secondary/5 ${className}`}>
      <Sparkles size={14} /> {label || LABEL[language] || LABEL.en}
    </button>
  )
}
