import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM || "",
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || ""
};

const keycloak = new Keycloak({
  ...keycloakConfig,
  // PKCE включается именно здесь
  pkceMethod: 'S256'
});

// Настройки инициализации PKCE + Code Flow
const keycloakProviderInitConfig = {
  onLoad: 'login-required',
  checkLoginIframe: false,
  pkceMethod: 'S256',
  silentCheckSsoRedirectUri:
    window.location.origin + '/silent-check-sso.html', // файл нужно добавить
};

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={keycloakProviderInitConfig}
      autoRefreshToken={true}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;