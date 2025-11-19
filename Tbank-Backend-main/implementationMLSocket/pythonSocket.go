package implementationMLSocket

import (
	"bufio"
	"fmt"
	loggerModule "main/loggerModule"
	mlModule "main/mlModule"
	"net"
)

type useSocketManager struct {
	Host string
	Port string
	logger loggerModule.LoggerManager
	
}

func NewUserSocketManager(Host string, Port string, logger loggerModule.LoggerManager) mlModule.MLManager{
	return &useSocketManager{
		Host: Host,
		Port: Port,
		logger: logger,
	}
}

func (sm *useSocketManager) Send(data string) (string, error) {
	connection, err := net.Dial("tcp", sm.Host+":"+sm.Port)
	if err != nil {
		sm.logger.ERROR("Failed to find Server")
		return "", err
	}
	
	defer connection.Close()

	sm.logger.DEBUG( data)
	fmt.Fprintf(connection, data)

	resp, err := bufio.NewReader(connection).ReadString('\n')
	if err != nil {
		sm.logger.ERROR("Failed get response")
		return "", err
	}

	sm.logger.DEBUG(resp)

	return resp[:len(resp)-1], nil

}