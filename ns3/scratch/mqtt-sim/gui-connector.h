#ifndef GUI_CONNECTOR_H
#define GUI_CONNECTOR_H

#include <arpa/inet.h>
#include <string>
#include <sys/socket.h>
#include <unistd.h>

class GuiConnector {
public:
  GuiConnector();
  ~GuiConnector();

  // Send a string message to the Python GUI
  void Send(std::string message);

private:
  int m_sock;
  struct sockaddr_in m_serverAddr;
};

// Global pointer to access the GUI from anywhere in the simulation
extern GuiConnector *g_gui;

#endif
