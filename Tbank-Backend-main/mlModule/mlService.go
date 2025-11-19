package mlModule

type MLService interface {
	Send(string) (string, error)
}