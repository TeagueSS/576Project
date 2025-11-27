#ifndef MQTT_APP_H
#define MQTT_APP_H

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/network-module.h"

using namespace ns3;

class MqttSensorApp : public Application {
public:
  MqttSensorApp();
  virtual ~MqttSensorApp();

  // Setup helper to define where to connect (Broker IP)
  void Setup(Address address, uint16_t port);

  static TypeId GetTypeId(void);

private:
  virtual void StartApplication(void) override;
  virtual void StopApplication(void) override;

  // The logic to send a message
  void PublishMessage();

  Ptr<Socket> m_socket;
  Address m_peerAddress;
  uint16_t m_peerPort;
  EventId m_sendEvent;
};

#endif
