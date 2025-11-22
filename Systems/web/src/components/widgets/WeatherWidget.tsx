import { useEffect, useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Cloud, Sun, CloudRain, CloudSnow, Wind, Droplets, Thermometer } from 'lucide-react';

interface WeatherData {
  temperature: number;
  condition: string;
  humidity: number;
  windSpeed: number;
  city: string;
  icon: string;
}

export const WeatherWidget = () => {
  const { t } = useI18n();
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWeather();
    const interval = setInterval(loadWeather, 300000); // Update every 5 minutes
    return () => clearInterval(interval);
  }, []);

  const loadWeather = async () => {
    try {
      setLoading(true);
      setError(null);
      // In a real implementation, this would call an API
      // For now, we'll use mock data
      // You can integrate with OpenWeatherMap, WeatherAPI, etc.
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate API call
      
      // Mock weather data
      const mockWeather: WeatherData = {
        temperature: 22,
        condition: 'Partly Cloudy',
        humidity: 65,
        windSpeed: 12,
        city: 'Moscow',
        icon: 'cloud',
      };
      
      setWeather(mockWeather);
    } catch (err) {
      setError(t('home.weather.error') || 'Failed to load weather');
      console.error('Error loading weather:', err);
    } finally {
      setLoading(false);
    }
  };

  const getWeatherIcon = (icon: string) => {
    switch (icon.toLowerCase()) {
      case 'sun':
      case 'clear':
        return Sun;
      case 'cloud':
      case 'cloudy':
        return Cloud;
      case 'rain':
        return CloudRain;
      case 'snow':
        return CloudSnow;
      default:
        return Cloud;
    }
  };

  if (loading) {
    return <div className="text-center py-4 oneui-text-muted">Loading...</div>;
  }

  if (error || !weather) {
    return (
      <div className="text-center py-8">
        <Cloud className="w-12 h-12 mx-auto mb-2 oneui-text-muted" />
        <p className="text-sm oneui-text-muted">{error || t('home.weather.noData') || 'No weather data'}</p>
      </div>
    );
  }

  const WeatherIcon = getWeatherIcon(weather.icon);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm oneui-text-muted">{weather.city}</p>
          <p className="text-3xl font-bold" style={{ color: 'var(--oneui-text)' }}>
            {weather.temperature}°C
          </p>
        </div>
        <WeatherIcon className="w-16 h-16" style={{ color: 'var(--oneui-primary)' }} />
      </div>
      
      <p className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
        {weather.condition}
      </p>

      <div className="grid grid-cols-3 gap-3 pt-3 border-t" style={{ borderColor: 'var(--oneui-border)' }}>
        <div className="flex items-center gap-2">
          <Droplets className="w-4 h-4" style={{ color: 'var(--oneui-info)' }} />
          <div>
            <p className="text-xs oneui-text-muted">{t('home.weather.humidity') || 'Humidity'}</p>
            <p className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
              {weather.humidity}%
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Wind className="w-4 h-4" style={{ color: 'var(--oneui-primary)' }} />
          <div>
            <p className="text-xs oneui-text-muted">{t('home.weather.wind') || 'Wind'}</p>
            <p className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
              {weather.windSpeed} km/h
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Thermometer className="w-4 h-4" style={{ color: 'var(--oneui-warning)' }} />
          <div>
            <p className="text-xs oneui-text-muted">{t('home.weather.feelsLike') || 'Feels'}</p>
            <p className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
              {weather.temperature + 2}°C
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

