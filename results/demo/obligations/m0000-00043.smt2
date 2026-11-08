(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 (not (= (ite (bvuge s_5 (_ bv20 8)) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let ((?x86 ((_ extract 4 0) s_5)))
(let (($x120 (bvule (_ bv20 5) ?x86)))
(let (($x72 (or (not (= ((_ extract 7 5) s_5) (_ bv0 3))) $x120)))
(not $x72)))))
(check-sat)
