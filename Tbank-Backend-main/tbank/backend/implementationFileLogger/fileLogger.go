package implementationFileLogger

import(
	"log"
	"os"
	loggerModule "main/loggerModule"
)

type fileLoggerManager struct{
	file *os.File
	logger *log.Logger
}

func NewFileLoggerManager(filePath string, prefix string) (loggerModule.LoggerManager, error){
	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)

	if err != nil{
		return nil, err
	}

	logger := log.New(file, prefix, log.LstdFlags)
	return &fileLoggerManager{file: file, logger: logger}, nil
}

func (flManager *fileLoggerManager) INFO(message string){
	flManager.logger.Println("INFO: " + message)
}

func (flManager *fileLoggerManager) WARNING(message string){
	flManager.logger.Println("WARNING: " + message)
}

func (flManager *fileLoggerManager) ERROR(message string){
	flManager.logger.Println("ERROR: " + message)
}

func (flManager *fileLoggerManager) DEBUG(message string){
	flManager.logger.Println("DEBUG: " + message)
}

func (flManager *fileLoggerManager) Close() error{
	return flManager.file.Close()
}