package mlModule

type MLManager interface {
	Send(string) (string, error)
}