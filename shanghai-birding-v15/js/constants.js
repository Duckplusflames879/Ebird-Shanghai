window.AppConstants = {
  DB_NAME: 'ShanghaiBirdingDB',
  DB_VERSION: 1,
  STORES: { RECORDS: 'records', APP: 'app' },
  ROUTES: {
    '/home': { title: '首页', kicker: 'Dashboard', module: 'Home' },
    '/weather': { title: '天气', kicker: '7-Day Forecast', module: 'Weather' },
    '/hotspots': { title: '观鸟点', kicker: 'Recent Sightings', module: 'Hotspots' },
    '/records': { title: '我的记录', kicker: 'Personal Database', module: 'My Records' },
    '/lexicon': { title: '图鉴', kicker: 'Local Bird Lexicon', module: 'Lexicon' },
    '/settings': { title: '设置', kicker: 'Data & Privacy', module: 'Settings' }
  }
};
