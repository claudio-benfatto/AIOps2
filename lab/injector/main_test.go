package main

import (
	"context"
	"testing"
)

func TestRun(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		wantErr bool
	}{
		{name: "no args", args: nil, wantErr: true},
		{name: "unknown command", args: []string{"bogus"}, wantErr: true},
		{name: "inject not yet implemented", args: []string{"inject"}, wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := run(context.Background(), tt.args)
			if (err != nil) != tt.wantErr {
				t.Fatalf("run(%v) error = %v, wantErr %v", tt.args, err, tt.wantErr)
			}
		})
	}
}
