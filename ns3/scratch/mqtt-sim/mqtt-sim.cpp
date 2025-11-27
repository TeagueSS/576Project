#include "gui-connector.h" // Need this to log to Python
#include "mqtt-app.h"

NS_OBJECT_ENSURE_REGISTERED(MqttSensorApp);

TypeId MqttSensorApp::GetTypeId(void) {
  static TypeId tid = TypeId("ns3::MqttSensorApp")
                          .SetParent<Application>()
                          .SetGroupName("Applications")
                          .AddConstructor<MqttSensorApp>();
  return tid;
}

MqttSensorApp::MqttSensorApp() : m_socket(0), m_peerPort(1883) {}

MqttSensorApp::~MqttSensorApp() { m_socket = 0; }

void MqttSensorApp::Setup(Address address, uint16_t port) {
  m_peerAddress = address;
  m_peerPort = port;
}

void MqttSensorApp::StartApplication(void) {
  m_socket = Socket::CreateSocket(GetNode(), TcpSocketFactory::GetTypeId());
  m_socket->Connect(InetSocketAddress(m_peerAddress, m_peerPort));

  // Start publishing after 1 second
  m_sendEvent =
      Simulator::Schedule(Seconds(1.0), &MqttSensorApp::PublishMessage, this);
}

void MqttSensorApp::StopApplication(void) {
  Simulator::Cancel(m_sendEvent);
  if (m_socket) {
    m_socket->Close();
  }
}

void MqttSensorApp::PublishMessage() {
  if (m_socket) {
    // Create payload
    std::string payload = "TEMP:" + std::to_string(20 + (rand() % 10));
    Ptr<Packet> packet =
        Create<Packet>((uint8_t *)payload.c_str(), payload.length());
    m_socket->Send(packet);

    // Log to GUI
    if (g_gui) {
      std::string log =
          "NODE_" + std::to_string(GetNode()->GetId()) + ":PUB:" + payload;
      g_gui->Send(log);
    }

    // Schedule next
    m_sendEvent =
        Simulator::Schedule(Seconds(2.0), &MqttSensorApp::PublishMessage, this);
  }
}
