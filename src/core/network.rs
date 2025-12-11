//! Network utilities with optional SOCKS5 proxy support.

use serde::{Deserialize, Serialize};
use std::net::SocketAddr;

/// Proxy configuration for network connections.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProxyConfig {
    /// Whether the proxy is enabled
    pub enabled: bool,
    /// Proxy host address
    pub host: Option<String>,
    /// Proxy port
    pub port: Option<u16>,
    /// Optional username for authentication
    pub username: Option<String>,
    /// Optional password for authentication
    pub password: Option<String>,
    /// Proxy type (socks5, http)
    #[serde(default = "default_proxy_type")]
    pub proxy_type: ProxyType,
}

fn default_proxy_type() -> ProxyType {
    ProxyType::Socks5
}

/// Supported proxy types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum ProxyType {
    #[default]
    Socks5,
    Http,
    Https,
}

impl ProxyConfig {
    /// Create a new SOCKS5 proxy configuration.
    pub fn socks5(host: impl Into<String>, port: u16) -> Self {
        Self {
            enabled: true,
            host: Some(host.into()),
            port: Some(port),
            username: None,
            password: None,
            proxy_type: ProxyType::Socks5,
        }
    }

    /// Create a new HTTP proxy configuration.
    pub fn http(host: impl Into<String>, port: u16) -> Self {
        Self {
            enabled: true,
            host: Some(host.into()),
            port: Some(port),
            username: None,
            password: None,
            proxy_type: ProxyType::Http,
        }
    }

    /// Add authentication credentials.
    pub fn with_auth(mut self, username: impl Into<String>, password: impl Into<String>) -> Self {
        self.username = Some(username.into());
        self.password = Some(password.into());
        self
    }

    /// Check if the proxy configuration is valid and enabled.
    pub fn is_active(&self) -> bool {
        self.enabled && self.host.is_some() && self.port.is_some()
    }

    /// Get the proxy URL string.
    pub fn url(&self) -> Option<String> {
        if !self.is_active() {
            return None;
        }

        let host = self.host.as_ref()?;
        let port = self.port?;
        let scheme = match self.proxy_type {
            ProxyType::Socks5 => "socks5",
            ProxyType::Http => "http",
            ProxyType::Https => "https",
        };

        match (&self.username, &self.password) {
            (Some(u), Some(p)) => Some(format!("{scheme}://{u}:{p}@{host}:{port}")),
            _ => Some(format!("{scheme}://{host}:{port}")),
        }
    }
}

/// Create a reqwest client with optional proxy support.
pub fn create_socket_with_proxy(
    proxy_cfg: &ProxyConfig,
) -> Result<reqwest::Client, reqwest::Error> {
    let mut builder = reqwest::Client::builder();

    if proxy_cfg.is_active() {
        if let Some(url) = proxy_cfg.url() {
            let proxy = reqwest::Proxy::all(&url)?;
            builder = builder.proxy(proxy);
        }
    }

    builder.build()
}

/// Network endpoint descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Endpoint {
    /// Endpoint address
    pub address: String,
    /// Endpoint port
    pub port: u16,
    /// Whether TLS should be used
    pub tls: bool,
    /// Optional endpoint name/label
    pub name: Option<String>,
}

impl Endpoint {
    /// Create a new endpoint.
    pub fn new(address: impl Into<String>, port: u16) -> Self {
        Self {
            address: address.into(),
            port,
            tls: false,
            name: None,
        }
    }

    /// Enable TLS for this endpoint.
    pub fn with_tls(mut self) -> Self {
        self.tls = true;
        self
    }

    /// Set a name for this endpoint.
    pub fn with_name(mut self, name: impl Into<String>) -> Self {
        self.name = Some(name.into());
        self
    }

    /// Get the full URL for this endpoint.
    pub fn url(&self) -> String {
        let scheme = if self.tls { "https" } else { "http" };
        format!("{scheme}://{}:{}", self.address, self.port)
    }

    /// Parse to a socket address (if the address is an IP).
    pub fn to_socket_addr(&self) -> Option<SocketAddr> {
        format!("{}:{}", self.address, self.port).parse().ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_proxy_config_disabled() {
        let cfg = ProxyConfig::default();
        assert!(!cfg.is_active());
        assert!(cfg.url().is_none());
    }

    #[test]
    fn test_proxy_config_socks5() {
        let cfg = ProxyConfig::socks5("127.0.0.1", 1080);
        assert!(cfg.is_active());
        assert_eq!(cfg.url(), Some("socks5://127.0.0.1:1080".to_string()));
    }

    #[test]
    fn test_proxy_config_with_auth() {
        let cfg = ProxyConfig::socks5("proxy.example.com", 1080).with_auth("user", "pass");
        assert_eq!(
            cfg.url(),
            Some("socks5://user:pass@proxy.example.com:1080".to_string())
        );
    }

    #[test]
    fn test_endpoint_url() {
        let ep = Endpoint::new("api.example.com", 443).with_tls();
        assert_eq!(ep.url(), "https://api.example.com:443");
    }
}
