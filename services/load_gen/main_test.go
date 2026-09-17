package main

import (
	"context"
	"testing"
	"time"
)

func TestRun(t *testing.T) {
	tests := []struct {
		name string
	}{
		{name: "returns when context is cancelled"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			cancel()

			done := make(chan error, 1)
			go func() { done <- run(ctx) }()

			select {
			case err := <-done:
				if err != nil {
					t.Fatalf("run() = %v, want nil", err)
				}
			case <-time.After(time.Second):
				t.Fatal("run() did not return after context cancellation")
			}
		})
	}
}
