(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 (not (= (ite (bvuge s_5 (_ bv10 8)) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x133 (= (bvand s_5 (_ bv224 8)) (_ bv0 8))))
(not $x133)))
(check-sat)
