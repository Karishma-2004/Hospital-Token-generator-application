import { Navigate, useParams } from 'react-router-dom';
export default function Book(){const {id}=useParams();return <Navigate to={`/doctors/${id}/slots`} replace/>;}
