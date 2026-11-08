(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (Array (_ BitVec 4) (_ BitVec 8)))
(assert
 (let ((?x20 ((as const (Array (_ BitVec 4) (_ BitVec 8))) (_ bv0 8))))
(let (($x26 (= s_6 ?x20)))
(let (($x11 (and $x26)))
(and $x11 true)))))
(check-sat)
