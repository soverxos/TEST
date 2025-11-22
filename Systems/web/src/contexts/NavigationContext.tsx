import { createContext, useContext, ReactNode } from 'react';

type NavigationContextType = {
  navigateTo: (section: string) => void;
};

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export const useNavigation = () => {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within NavigationProvider');
  }
  return context;
};

export const NavigationProvider = ({
  children,
  navigateTo,
}: {
  children: ReactNode;
  navigateTo: (section: string) => void;
}) => {
  return (
    <NavigationContext.Provider value={{ navigateTo }}>
      {children}
    </NavigationContext.Provider>
  );
};

