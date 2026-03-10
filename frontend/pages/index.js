import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import { Box, Button, Container, Typography } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

export default function Home() {
  const router = useRouter();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    const fetchCars = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/cars`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.status === 401) {
          localStorage.removeItem('token');
          router.push('/login');
          return;
        }
        const data = await res.json();
        setRows(data.map((item) => ({ id: item.id, ...item })));
      } catch (err) {
        setRows([]);
      } finally {
        setLoading(false);
      }
    };

    fetchCars();
  }, [router]);

  const columns = useMemo(() => [
    { field: 'brand', headerName: 'Марка', flex: 1 },
    { field: 'model', headerName: 'Модель', flex: 1 },
    { field: 'year', headerName: 'Год', width: 100 },
    { field: 'price', headerName: 'Цена', width: 120 },
    { field: 'color', headerName: 'Цвет', width: 120 },
    { field: 'url', headerName: 'Ссылка', flex: 1,
      renderCell: (params) => (<a href={params.value} target="_blank" rel="noreferrer">Открыть</a>)
    }
  ], []);

  const logout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return (
    <Box sx={{ minHeight: '100vh', background: 'linear-gradient(180deg, #f5f3ef 0%, #eae3db 100%)', py: 4 }}>
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4">Автообъявления</Typography>
          <Button variant="outlined" onClick={logout}>Выйти</Button>
        </Box>
        <Box sx={{ height: 600, background: '#fff' }}>
          <DataGrid rows={rows} columns={columns} loading={loading} pageSizeOptions={[10, 25, 50]} />
        </Box>
      </Container>
    </Box>
  );
}
