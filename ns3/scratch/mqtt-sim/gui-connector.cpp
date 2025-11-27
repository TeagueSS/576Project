#include "gui-connector.h"
#include <cstring>
#include <iostream>

GuiConnector *g_gui = nullptr;

GuiConnector::GuiConnector() {
  m_sock = socket(AF_INET, SOCK_DGRAM, 0);
  if (m_sock < 0) {
    std::cerr << "[Error] Could not create GUI socket" << std::endl;
  }

  memset(&m_serverAddr, 0, sizeof(m_serverAddr));
  m_serverAddr.sin_family = AF_INET;
  m_serverAddr.sin_port = htons(5555);
  inet_pton(AF_INET, "127.0.0.1", &m_serverAddr.sin_addr);
}

GuiConnector::~GuiConnector() {
  if (m_sock >= 0) {
    close(m_sock);
  }
}

void GuiConnector::Send(std::string message) {
  if (m_sock >= 0) {
    sendto(m_sock, message.c_str(), message.length(), 0,
           (struct sockaddr *)&m_serverAddr, sizeof(m_serverAddr));
  }
}
