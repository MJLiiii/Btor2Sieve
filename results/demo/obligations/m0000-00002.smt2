(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 (not (= (ite (bvuge s_5 (_ bv10 8)) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let ((?x51 ((_ extract 3 0) s_5)))
(let (($x47 (bvule (_ bv10 4) ?x51)))
(let (($x50 (or (not (= ((_ extract 7 4) s_5) (_ bv0 4))) $x47)))
(not $x50)))))
(check-sat)
