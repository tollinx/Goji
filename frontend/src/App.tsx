import { useRef } from 'react';
import MenuPage from './components/MenuPage';
import AskPage from './components/AskPage';
import ThemeToggle from './components/ThemeToggle';
import { useTheme } from './hooks/useTheme';
import './App.css';

function App() {
  const askRef = useRef<HTMLElement>(null);
  const { theme, toggle } = useTheme();

  const scrollToAsk = () => {
    askRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <>
      <ThemeToggle theme={theme} onToggle={toggle} />
      <div className="scroller">
        <MenuPage onScrollToAsk={scrollToAsk} />
        <AskPage ref={askRef} />
      </div>
    </>
  );
}

export default App;
