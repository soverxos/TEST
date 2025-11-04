import { useTheme } from '../contexts/ThemeContext';

export const AnimatedBackground = () => {
  const { theme } = useTheme();

  return (
    <div className="animated-background">
      <div className="gradient-orb orb-1"></div>
      <div className="gradient-orb orb-2"></div>
      <div className="gradient-orb orb-3"></div>
      {theme === 'dark' && (
        <>
          <div className="light-beam beam-1"></div>
          <div className="light-beam beam-2"></div>
          <div className="light-beam beam-3"></div>
        </>
      )}
    </div>
  );
};
