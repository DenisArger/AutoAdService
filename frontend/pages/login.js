import { useState } from 'react';
import { useRouter } from 'next/router';
import { Box, Button, Container, Paper, TextField, Typography } from '@mui/material';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) {
        setError('Неверные данные');
        return;
      }
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      router.push('/');
    } catch (err) {
      setError('Ошибка сети');
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', background: 'linear-gradient(135deg, #f5f3ef 0%, #e7e1d9 100%)' }}>
      <Container maxWidth="sm">
        <Paper elevation={8} sx={{ p: 4 }}>
          <Typography variant="h4" sx={{ mb: 2 }}>Вход</Typography>
          <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary' }}>Введите логин администратора</Typography>
          <Box component="form" onSubmit={onSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <TextField label="Пароль" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {error && <Typography color="error">{error}</Typography>}
            <Button variant="contained" type="submit">Войти</Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}
