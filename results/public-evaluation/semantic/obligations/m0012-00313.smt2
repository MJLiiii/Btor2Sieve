(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x159 (bvor (bvshl i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x2283 (bvor (bvlshr i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x722 (ite (and (distinct ?x2283 ?x159) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x722 (_ bv1 1)))))))
(assert
 (let (($x138 (bvule i_4 (_ bv2 3))))
(not $x138)))
(check-sat)
