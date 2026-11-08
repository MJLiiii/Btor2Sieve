(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x343 (bvor (bvlshr i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
 (let ((?x47 (ite (and (distinct ?x343 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x47 (_ bv1 1))))))
(assert
 (let ((?x343 (bvor (bvlshr i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
(let (($x2875 (= ?x343 (_ bv1 3))))
(not $x2875))))
(check-sat)
