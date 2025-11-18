package mlModule

import (
	"errors"
)

var (
	ErrBadUser         = errors.New("User not found")
	ErrNoModel         = errors.New("Model was not found")
	ErrBadFile         = errors.New("Invalid File sent")
	ErrInternalMLError = errors.New("Error happened during ML model")
)

type mlService struct {
	mlManager MLManager
}

func NewMLService(mlManager MLManager) MLService {
	return &mlService{
		mlManager: mlManager,
	}
}

func (mls *mlService) Send(s string) (string, error) {
	return mls.mlManager.Send(s)
}